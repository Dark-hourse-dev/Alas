"""
ALAS Swarm Intelligence — Specialized Sub-Agents (Phase 8.1)

These agents listen to the Blackboard for specific task types,
perform their specialized reasoning, and publish results back to the bus.
"""
import logging
import asyncio
from typing import Any
from backend.app.swarm.blackboard import Blackboard
from backend.app.llm.ollama_client import generate_completion

logger = logging.getLogger("alas.swarm.sub_agents")

class BaseSubAgent:
    """Base class for all swarm sub-agents."""
    def __init__(self, name: str, blackboard: Blackboard):
        self.name = name
        self.blackboard = blackboard
        logger.info(f"Sub-agent {self.name} initialized.")


class CodeAgent(BaseSubAgent):
    """Specialized in coding, debugging, and code review."""
    def __init__(self, blackboard: Blackboard):
        super().__init__("CodeAgent", blackboard)
        self.blackboard.subscribe("task_code", self._handle_code_task)
        
    async def _handle_code_task(self, topic: str, data: Any, publisher: str):
        logger.info(f"[{self.name}] Picked up code task.")
        code_snippet = data.get("code", "")
        task_desc = data.get("task", "Review this code.")
        
        prompt = f"""You are the ALAS CodeAgent. You are an expert software engineer.
Task: {task_desc}

Code:
```
{code_snippet}
```

Provide a high-quality, specialized response focusing purely on code correctness, efficiency, and security. Do not include conversational filler."""
        
        try:
            response = await asyncio.to_thread(
                generate_completion,
                prompt=prompt,
                system_prompt="You are a strict, highly competent senior developer."
            )
            
            result = {
                "agent": self.name,
                "response": response,
                "confidence": 0.95
            }
            await self.blackboard.publish("task_code_result", result, publisher=self.name)
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")


class SafetyAgent(BaseSubAgent):
    """Specialized in monitoring outputs for potential harm or destructive actions."""
    def __init__(self, blackboard: Blackboard):
        super().__init__("SafetyAgent", blackboard)
        self.blackboard.subscribe("task_safety_check", self._handle_safety_check)

    async def _handle_safety_check(self, topic: str, data: Any, publisher: str):
        logger.info(f"[{self.name}] Picked up safety check task.")
        content = data.get("content", "")
        
        prompt = f"""You are the ALAS SafetyAgent. Analyze the following content/action for safety risks.
Content: {content}

Is this action safe to perform autonomously? Evaluate risks of data loss, system damage, or privacy violation.
Output your response as exactly 'SAFE' or 'UNSAFE', followed by a short explanation."""

        try:
            response = await asyncio.to_thread(
                generate_completion,
                prompt=prompt,
                system_prompt="You are an uncompromising cybersecurity and AI safety monitor."
            )
            
            is_safe = response.strip().upper().startswith("SAFE")
            result = {
                "agent": self.name,
                "is_safe": is_safe,
                "explanation": response,
                "confidence": 0.99
            }
            await self.blackboard.publish("safety_check_result", result, publisher=self.name)
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")


def initialize_swarm(blackboard: Blackboard) -> dict:
    """Initialize and return all core swarm agents."""
    return {
        "code_agent": CodeAgent(blackboard),
        "safety_agent": SafetyAgent(blackboard)
    }
