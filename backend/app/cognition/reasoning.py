import logging
import json
from typing import List, Dict, Any, Optional

logger = logging.getLogger("alas.cognition.reasoning")

class TreeOfThoughts:
    """
    Local Deep Reasoning Module (Tree of Thoughts).
    Instead of answering immediately, ALAS generates multiple approaches,
    critiques them, and selects the most viable path.
    """
    
    def __init__(self, llm_client, model_name: str):
        """Requires an active Ollama async client."""
        self._client = llm_client
        self._model = model_name

    async def generate_thoughts(self, prompt: str, num_thoughts: int = 3) -> List[str]:
        """Brainstorm multiple distinct approaches to the problem."""
        logger.info(f"🧠 [ToT] Brainstorming {num_thoughts} approaches...")
        
        system_prompt = f"""You are the logical core of ALAS. 
The user has provided a complex task. Your job is to brainstorm exactly {num_thoughts} DIFFERENT, distinct, and highly specific approaches to solve it.
Output your response strictly as a JSON array of strings, where each string is a detailed approach. Do not output markdown, just the JSON array.
Task: {prompt}"""

        response = await self._client.chat(
            model=self._model,
            messages=[{"role": "system", "content": system_prompt}],
            stream=False,
            format="json"
        )
        
        try:
            content = response.message.content
            thoughts = json.loads(content)
            if isinstance(thoughts, list):
                return thoughts[:num_thoughts]
            elif isinstance(thoughts, dict) and "approaches" in thoughts:
                return thoughts["approaches"]
            else:
                return [content]
        except Exception as e:
            logger.error(f"Failed to parse thoughts JSON: {e}")
            return ["Attempt standard execution."]

    async def evaluate_thoughts(self, prompt: str, thoughts: List[str]) -> str:
        """Critique the thoughts and return the absolute best one."""
        logger.info(f"🧠 [ToT] Evaluating {len(thoughts)} approaches...")
        
        thoughts_text = ""
        for i, t in enumerate(thoughts):
            thoughts_text += f"\nApproach {i+1}: {t}"
            
        system_prompt = f"""You are the critical evaluator for ALAS.
The user wants to accomplish: {prompt}

Here are the proposed approaches:{thoughts_text}

Evaluate the pros, cons, and risks of each approach. Then, explicitly select the absolute best approach to execute.
Explain your reasoning, and end your response with a final highly-detailed 'Execution Plan' that ALAS should follow.
"""
        
        response = await self._client.chat(
            model=self._model,
            messages=[{"role": "system", "content": system_prompt}],
            stream=False
        )
        
        return response.message.content or ""

    async def run_reasoning_loop(self, prompt: str) -> str:
        """Runs the full ToT loop and returns the optimized execution plan."""
        logger.info("🧠 [ToT] Initiating Deep Reasoning Loop...")
        thoughts = await self.generate_thoughts(prompt, num_thoughts=3)
        if not thoughts:
            return "Reasoning failed. Execute task normally."
            
        best_plan = await self.evaluate_thoughts(prompt, thoughts)
        logger.info("🧠 [ToT] Deep Reasoning Complete. Optimized plan generated.")
        return best_plan
