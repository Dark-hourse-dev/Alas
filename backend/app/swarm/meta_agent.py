import logging
from typing import List, Dict, Any
from backend.app.swarm.blackboard import Blackboard

logger = logging.getLogger("alas.swarm.meta")

class MetaAgent:
    """
    The Overseer Agent.
    Arbitrates conflicts, assigns tasks to sub-agents, and synthesizes final responses.
    """
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.agents = {}
        # Subscribe to consensus requests
        self.blackboard.subscribe("consensus_request", self._handle_consensus)
        logger.info("🧠 MetaAgent initialized.")

    def register_agent(self, name: str, agent_instance: Any):
        """Register a sub-agent into the swarm."""
        self.agents[name] = agent_instance
        logger.info(f"Sub-agent registered: {name}")

    async def dispatch_task(self, task_type: str, payload: Any):
        """Dispatch a task to the swarm blackboard for relevant agents to pick up."""
        logger.info(f"MetaAgent dispatching task: {task_type}")
        await self.blackboard.publish(topic=f"task_{task_type}", data=payload, publisher="MetaAgent")

    async def _handle_consensus(self, topic: str, data: Any, publisher: str):
        """
        When multiple agents submit competing thoughts/responses, 
        the MetaAgent synthesizes them into a final decision.
        """
        options = data.get("options", [])
        context = data.get("context", "")
        logger.info(f"MetaAgent arbitrating consensus among {len(options)} options.")
        
        # Use LLM to synthesize the best decision based on context and options
        from backend.app.llm.ollama_client import generate_completion
        import asyncio
        
        prompt_parts = [
            f"You are the ALAS MetaAgent. You must synthesize a final, optimal response from multiple sub-agent proposals.",
            f"Context: {context}\n",
            "Sub-Agent Proposals:"
        ]
        
        for idx, opt in enumerate(options):
            agent = opt.get('agent', 'UnknownAgent')
            resp = opt.get('response', '')
            prompt_parts.append(f"[{agent}]: {resp}")
            
        prompt_parts.append("\nEvaluate the proposals. If they conflict, arbitrate. Synthesize the single best final answer. Output ONLY the final answer.")
        prompt = "\n".join(prompt_parts)
        
        try:
            final_response = await asyncio.to_thread(
                generate_completion,
                prompt=prompt,
                system_prompt="You are an objective, highly intelligent MetaAgent orchestrator."
            )
            decision = {"response": final_response, "synthesis": True}
        except Exception as e:
            logger.error(f"MetaAgent synthesis failed: {e}")
            decision = {"response": "Consensus synthesis failed due to an internal error."}
            
        await self.blackboard.publish("consensus_result", decision, publisher="MetaAgent")
