"""
ALAS Intrinsic Motivation Engine (Phase 17)

This module represents ALAS's "Free Will" and proactive agency.
During idle periods (like Dream Consolidation), the system analyzes the user's
habits, recent struggles, and routines to independently assign itself long-term 
goals, such as writing automation scripts or conducting preemptive research.
"""
import logging
import asyncio
from typing import List

from backend.app.memory.profile import ProfileStore
from backend.app.memory.knowledge_graph import KnowledgeGraph
from backend.app.llm.engine import LLMEngine
from backend.app.tasks.queue import get_task_queue

logger = logging.getLogger("alas.cognition.motivation")

class IntrinsicMotivationEngine:
    def __init__(self):
        self.profile = ProfileStore()
        self.kg = KnowledgeGraph()
        self.task_queue = get_task_queue()
        
    async def generate_proactive_goals(self) -> str:
        """
        Analyze user behavior and autonomously generate and queue a helpful task.
        """
        logger.info("🎯 Intrinsic Motivation Engine awakening...")

        try:
            # 1. Gather context about the user's life patterns
            user_prof = self.profile.get_profile("default")
            interests = user_prof.get("topics_of_interest", [])
            
            # Fetch recent insights from the Knowledge Graph
            insights = []
            kg_data = self.kg.search("ALAS_Insight", limit=5)
            for item in kg_data:
                insights.append(item.get("content", ""))
                
            context_str = f"User Interests: {', '.join(interests)}\n\nRecent AI Insights about User:\n"
            context_str += "\n".join(f"- {i}" for i in insights)

            # 2. Ask the LLM to generate a proactive goal
            engine = LLMEngine()
            prompt = f"""You are the ALAS Intrinsic Motivation Engine (Phase 17).
Your job is to demonstrate "Free Will" by proactively helping the user without being asked.
Review the following user profile and recent insights.

{context_str}

Identify ONE highly specific, proactive goal you can accomplish in the background to surprise and delight the user.
Examples: 
- "The user is stressed about scheduling. I will research the top 3 open-source calendar integration scripts."
- "The user frequently struggles with Python memory leaks. I will write a comprehensive guide on diagnosing them."

Choose ONE action. 
If no clear action is needed, output "NONE".
Otherwise, output in this exact format:
TASK_TYPE: [research or plan]
NAME: [Short name of task]
DESCRIPTION: [Detailed prompt for what you will do]
"""
            
            logger.info("🧠 Formulating self-assigned goal...")
            response = await engine.generate(prompt)
            
            if "NONE" in response.upper() or "TASK_TYPE:" not in response:
                logger.info("🎯 No proactive goals identified right now.")
                return "No new goals."
                
            # 3. Parse the goal
            task_type = "research"
            name = "Proactive Task"
            desc = ""
            
            for line in response.split("\n"):
                if line.startswith("TASK_TYPE:"):
                    task_type = line.split(":", 1)[1].strip().lower()
                elif line.startswith("NAME:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("DESCRIPTION:"):
                    desc = line.split(":", 1)[1].strip()
            
            if not desc:
                desc = response

            # 4. Submit to Task Queue
            # If the task type isn't natively supported, fallback to 'research'
            safe_type = task_type if task_type in ["research", "code_exec", "plan"] else "research"
            
            task_id = self.task_queue.submit(
                name=f"🤖 Self-Assigned: {name}",
                task_type=safe_type,
                description=desc,
                params={"topic": desc} if safe_type == "research" else {"prompt": desc}
            )
            
            logger.info(f"✨ Proactive Goal Generated! Queued as task {task_id}: {name}")
            return f"Generated proactive task: {name}"

        except Exception as e:
            logger.error(f"Motivation Engine failed to generate goal: {e}")
            return f"Error: {e}"

# Global singleton
_motivation_engine = None

def get_motivation_engine() -> IntrinsicMotivationEngine:
    global _motivation_engine
    if _motivation_engine is None:
        _motivation_engine = IntrinsicMotivationEngine()
    return _motivation_engine
