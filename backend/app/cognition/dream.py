"""
ALAS Meta-Intelligence — Dream Consolidation (Phase 10.4)

Runs during idle periods to "dream" by replaying and recombining 
recent memories to generate novel insights and compress knowledge.
"""
import logging
import asyncio

logger = logging.getLogger("alas.cognition.dream")

class DreamConsolidator:
    def __init__(self):
        from backend.app.memory.retrieval import MemoryRetriever
        self.retriever = MemoryRetriever()
        
    async def trigger_dream_cycle(self) -> str:
        """
        Trigger a dream sequence where ALAS reflects on recent interactions,
        finds patterns, and stores the synthesis as a permanent insight.
        """
        from backend.app.llm.ollama_client import generate_completion
        
        logger.info("🌌 Initiating Dream Consolidation Cycle...")
        
        # 1. Fetch recent episodic memories
        # In a real implementation, we'd query ChromaDB for the last 24 hours of interactions.
        # Here we mock the extraction of the most recent interactions.
        try:
            recent_context = self.retriever.retrieve_context("what happened recently?", mode="work")
            memories = recent_context.get("composed_context", "No recent memories to consolidate.")
        except Exception as e:
            memories = f"Error retrieving memories: {e}"

        if "No recent memories" in memories:
            logger.info("🌌 Dream Cycle skipped: Insufficient recent memory.")
            return "No recent memories to dream about."

        # 2. Dream prompt (Insight synthesis)
        prompt = f"""You are in a dream state, synthesizing insights from recent memories.
        
Recent Memories:
{memories}

Task:
1. Identify any hidden patterns or emotional themes in these interactions.
2. Generate ONE profound, novel insight about the user based on these events.
3. Formulate this insight as a permanent rule or fact to remember.

Output ONLY the final Insight Rule."""

        try:
            insight = await asyncio.to_thread(
                generate_completion,
                prompt=prompt,
                system_prompt="You are an unconscious mind processing memories."
            )
            
            logger.info(f"🌌 Dream Insight Generated: {insight}")
            
            # 3. Store the insight back into long-term knowledge
            from backend.app.memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            kg.add_entity("ALAS_Insight", entity_type="concept", properties={"content": insight}, source="dream_cycle")
            kg.add_relationship("User", "ALAS_Insight", relation="associated_with", context="dream_consolidation")
            
            # 4. Phase 17: Intrinsic Motivation (Free Will)
            # Use this new insight to formulate a proactive goal in the background
            from backend.app.cognition.intrinsic_motivation import get_motivation_engine
            motivation = get_motivation_engine()
            goal_result = await motivation.generate_proactive_goals()
            
            # 5. Phase 20: Federated Hive-Mind
            # Share this abstract insight with the global ALAS network
            from backend.app.learning.federated import get_hive_mind
            hive = get_hive_mind()
            await hive.broadcast_abstract_skill(
                skill_name="Dream Insight",
                skill_logic=insight,
                domain="user_psychology"
            )
            
            return f"Dream cycle complete. Insight consolidated: {insight}\nMotivation Status: {goal_result}"
        except Exception as e:
            logger.error(f"🌌 Dream cycle failed: {e}")
            return f"Dream cycle failed: {e}"

# Expose as a tool wrapper
def execute_dream_cycle() -> str:
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(DreamConsolidator().trigger_dream_cycle())).result(timeout=60)
        else:
            return asyncio.run(DreamConsolidator().trigger_dream_cycle())
    except Exception as e:
        return f"Failed to execute dream cycle: {e}"
