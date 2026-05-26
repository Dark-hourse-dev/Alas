"""
ALAS LLM Engine — Ollama-powered inference with streaming.

Wraps Ollama for local LLM inference with support for:
- Streaming token generation
- Memory-augmented prompts
- Mode-aware personality switching
"""

from typing import AsyncGenerator, Optional

import ollama

from backend.app.config import get_settings
from backend.app.llm.prompts import build_system_prompt
from backend.app.memory.retrieval import MemoryRetriever


class LLMEngine:
    """
    Core LLM inference engine using Ollama.
    
    Supports streaming generation with memory-augmented context
    and mode-aware system prompts.
    """

    def __init__(self):
        settings = get_settings()
        self._client = ollama.AsyncClient(host=settings.ollama_host)
        self._model = settings.ollama_model
        self._retriever = MemoryRetriever()

    async def generate(
        self,
        message: str,
        session_id: Optional[str] = None,
        mode: str = "casual",
        user_id: str = "default",
        conversation_history: Optional[list[dict]] = None,
    ) -> str:
        """
        Generate a complete response (non-streaming).
        
        Args:
            message: User's input message.
            session_id: Current session identifier.
            mode: Interaction mode.
            user_id: User identifier.
            conversation_history: Recent chat messages for context.
            
        Returns:
            Complete response text.
        """
        # Retrieve memory context
        context = self._retriever.retrieve_context(
            query=message,
            session_id=session_id,
            mode=mode,
            user_id=user_id,
        )

        # Build system prompt with mode + memory context
        system_prompt = build_system_prompt(
            mode=mode,
            user_context=context["composed_context"],
        )

        # Inject behavioral evolution modifiers
        from backend.app.learning.evolution import get_evolution_system
        modifiers = get_evolution_system().get_prompt_modifiers()
        system_prompt += f"\n\n[BEHAVIORAL DIRECTIVE]: {modifiers}"

        # Compose messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages

        messages.append({"role": "user", "content": message})

        # Generate response
        response = await self._client.chat(
            model=self._model,
            messages=messages,
        )

        assistant_message = response.message.content

        # Store both user and assistant messages in episodic memory
        self._retriever.store_interaction(
            content=message,
            role="user",
            mode=mode,
            session_id=session_id,
            user_id=user_id,
        )
        self._retriever.store_interaction(
            content=assistant_message,
            role="assistant",
            mode=mode,
            session_id=session_id,
            user_id=user_id,
        )

        return assistant_message

    async def generate_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        mode: str = "casual",
        user_id: str = "default",
        conversation_history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response, yielding tokens as they arrive.
        
        Args:
            message: User's input message.
            session_id: Current session identifier.
            mode: Interaction mode.
            user_id: User identifier.
            conversation_history: Recent chat messages for context.
            
        Yields:
            Individual tokens/chunks as they are generated.
        """
        # Retrieve memory context
        context = self._retriever.retrieve_context(
            query=message,
            session_id=session_id,
            mode=mode,
            user_id=user_id,
        )

        # Build system prompt
        system_prompt = build_system_prompt(
            mode=mode,
            user_context=context["composed_context"],
        )

        # Inject behavioral evolution modifiers
        from backend.app.learning.evolution import get_evolution_system
        modifiers = get_evolution_system().get_prompt_modifiers()
        system_prompt += f"\n\n[BEHAVIORAL DIRECTIVE]: {modifiers}"

        # Compose messages
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": message})

        # Store user message immediately
        self._retriever.store_interaction(
            content=message,
            role="user",
            mode=mode,
            session_id=session_id,
            user_id=user_id,
        )

        # ReAct Loop for Tool Execution
        from backend.app.llm.tools import AVAILABLE_TOOLS, execute_tool

        full_response = []
        max_iterations = 3
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            iteration_response = []
            
            stream = await self._client.chat(
                model=self._model,
                messages=messages,
                stream=True,
                tools=AVAILABLE_TOOLS,
            )

            tool_calls = []
            async for chunk in stream:
                if hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:
                    tool_calls.extend(chunk.message.tool_calls)
                
                token = chunk.message.content
                if token:
                    iteration_response.append(token)
                    full_response.append(token)
                    yield token

            if tool_calls:
                # Add assistant message containing the tool calls
                ast_msg = {
                    "role": "assistant",
                    "content": "".join(iteration_response),
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                }
                messages.append(ast_msg)
                
                # Execute tools
                for tc in tool_calls:
                    yield f"\n\n_⚙️ Using tool: `{tc.function.name}`..._\n\n"
                    res = execute_tool(tc)
                    messages.append(res)
                
                # Continue loop to generate final answer
                continue
            else:
                # No tool calls, generation is complete
                break

        # Store complete assistant response
        complete_response = "".join(full_response)
        self._retriever.store_interaction(
            content=complete_response,
            role="assistant",
            mode=mode,
            session_id=session_id,
            user_id=user_id,
        )

    async def check_health(self) -> dict:
        """Check if Ollama is available and the model is loaded."""
        try:
            models_resp = await self._client.list()
            # Handle both dict and object response from ollama
            if isinstance(models_resp, dict):
                model_list = models_resp.get("models", [])
            else:
                model_list = models_resp.models if hasattr(models_resp, 'models') else []
            model_names = []
            for m in model_list:
                if isinstance(m, dict):
                    model_names.append(m.get("name", m.get("model", "")))
                else:
                    model_names.append(getattr(m, "name", getattr(m, "model", "")))
            model_available = any(self._model in name for name in model_names)
            return {
                "status": "healthy" if model_available else "model_not_found",
                "ollama_connected": True,
                "model": self._model,
                "model_available": model_available,
                "available_models": model_names,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "ollama_connected": False,
                "model": self._model,
                "error": str(e),
            }

    @property
    def retriever(self) -> MemoryRetriever:
        """Access the memory retriever."""
        return self._retriever
