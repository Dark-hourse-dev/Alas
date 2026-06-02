"""
ALAS LLM Engine — Ollama-powered inference with streaming.

Wraps Ollama for local LLM inference with support for:
- Streaming token generation
- Memory-augmented prompts
- Mode-aware personality switching
"""

import json
import logging
import asyncio
from typing import AsyncGenerator, Optional

import ollama

from backend.app.config import get_settings
from backend.app.llm.prompts import build_system_prompt
from backend.app.memory.retrieval import MemoryRetriever
from backend.app.proactive.context import get_context_engine


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
        evolution = get_evolution_system()
        modifiers = evolution.get_prompt_modifiers()
        system_prompt += f"\n\n[BEHAVIORAL DIRECTIVE]: {modifiers}"
        
        # Inject Phase 4 Context
        env_context = get_context_engine().build_context_prompt(evolution.current_genome.get("proactivity_threshold", 0.5))
        system_prompt += env_context
        
        # Inject Phase 19 Emotional State
        from backend.app.cognition.emotion import get_emotion_machine
        emotion_modifier = get_emotion_machine().get_prompt_modifier()
        system_prompt += f"\n\n[EMOTIONAL STATE]: {emotion_modifier}"

        # Compose messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages

        messages.append({"role": "user", "content": message})

        # -------------------------------------------------------------
        # ALAS 2.0 Mixture of Compute Router (Phase 12)
        # -------------------------------------------------------------
        from backend.app.llm.router import get_semantic_router
        router = get_semantic_router()
        route = router.route(message)
        
        if route == "cloud":
            from backend.app.llm.cloud_engine import get_cloud_engine
            cloud = get_cloud_engine()
            assistant_message = await cloud.generate_complete(messages)
        else:
            # Generate response via Local Ollama
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
        evolution = get_evolution_system()
        modifiers = evolution.get_prompt_modifiers()
        system_prompt += f"\n\n[BEHAVIORAL DIRECTIVE]: {modifiers}"
        
        # Inject Phase 4 Context
        env_context = get_context_engine().build_context_prompt(evolution.current_genome.get("proactivity_threshold", 0.5))
        system_prompt += env_context
        
        # Inject Phase 19 Emotional State
        from backend.app.cognition.emotion import get_emotion_machine
        emotion_modifier = get_emotion_machine().get_prompt_modifier()
        system_prompt += f"\n\n[EMOTIONAL STATE]: {emotion_modifier}"

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

        # -------------------------------------------------------------
        # ALAS 2.0 Mixture of Compute Router (Phase 12)
        # -------------------------------------------------------------
        from backend.app.llm.router import get_semantic_router
        router = get_semantic_router()
        route = router.route(message)
        
        if route == "cloud":
            yield "\n\n_☁️ [Mixture of Compute] Task complexity exceeds local thresholds. Routing to Cloud..._\n\n"
            from backend.app.llm.cloud_engine import get_cloud_engine
            cloud = get_cloud_engine()
            
            full_cloud_response = []
            async for chunk in cloud.generate_stream(messages):
                full_cloud_response.append(chunk)
                yield chunk
                
            self._retriever.store_interaction(
                content="".join(full_cloud_response),
                role="assistant",
                mode=mode,
                session_id=session_id,
                user_id=user_id,
            )
            return

        # -------------------------------------------------------------
        # ALAS 2.0 Local Superintelligence (Tree-of-Thoughts)
        # -------------------------------------------------------------
        msg_lower = message.lower()
        if "[think]" in msg_lower or "refactor" in msg_lower or "complex" in msg_lower:
            yield "\n\n_🧠 [Local Superintelligence] Deep Reasoning Activated. ALAS is brainstorming approaches..._\n\n"
            from backend.app.cognition.reasoning import TreeOfThoughts
            tot = TreeOfThoughts(self._client, self._model)
            
            best_plan = await tot.run_reasoning_loop(message)
            
            # Inject the optimized plan into the system prompt for execution
            messages[0]["content"] += f"\n\n[DEEP REASONING PLAN]:\nThe following is an optimized execution plan you generated via Tree-of-Thoughts. Follow this plan to solve the user's task:\n{best_plan}"
            
            yield f"_🧠 [Local Superintelligence] Plan synthesized. Executing..._\n\n"
            
        # Local ReAct Loop for Tool Execution (Ollama)
        from backend.app.llm.tool_registry import get_all_tools, execute_tool

        full_response = []
        max_iterations = 3
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Use stream=False for reliable tool calling in Ollama
            response = await self._client.chat(
                model=self._model,
                messages=messages,
                stream=False,
                tools=get_all_tools(),
            )

            msg = response.message
            
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                # Add assistant message containing the tool calls
                ast_msg = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in msg.tool_calls
                    ]
                }
                messages.append(ast_msg)
                
                # Execute tools
                for tc in msg.tool_calls:
                    yield f"\n\n_⚙️ Using tool: `{tc.function.name}`..._\n\n"
                    res = await execute_tool(tc)
                    messages.append(res)
                
                # Continue loop to allow model to read tool results
                continue
            else:
                # No tool calls, generation is complete. Simulate streaming.
                final_text = msg.content or ""
                
                # Simulate streaming by yielding chunks
                chunk_size = 4
                for i in range(0, len(final_text), chunk_size):
                    chunk = final_text[i:i+chunk_size]
                    full_response.append(chunk)
                    yield chunk
                    await asyncio.sleep(0.01) # Slight delay for smooth UI streaming
                    
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
