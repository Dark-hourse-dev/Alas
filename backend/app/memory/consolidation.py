"""
ALAS Memory Consolidation Engine — Bio-inspired memory processing.

Inspired by sleep-cycle memory consolidation in mammals:
1. Reviews recent episodic memories
2. Extracts key entities/relationships via LLM
3. Promotes insights to the knowledge graph (L2)
4. Applies forgetting curve to low-relevance entries

Can be run on-demand or scheduled as a background task.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from backend.app.memory.episodic import EpisodicMemory
from backend.app.memory.knowledge_graph import KnowledgeGraph
from backend.app.llm.extractors import extract_entities, extract_user_facts

logger = logging.getLogger("alas.memory.consolidation")


class ConsolidationEngine:
    """
    Bio-inspired memory consolidation processor.

    Mimics hippocampal replay: reviews episodic memories,
    extracts semantic knowledge, and promotes it to L2.
    """

    def __init__(self):
        self.episodic = EpisodicMemory()
        self.knowledge_graph = KnowledgeGraph()

    async def consolidate(
        self,
        session_id: Optional[str] = None,
        max_memories: int = 50,
    ) -> dict:
        """
        Run a full consolidation cycle.

        Args:
            session_id: Optional — consolidate only a specific session.
            max_memories: Maximum memories to process.

        Returns:
            Summary of consolidation results.
        """
        logger.info("🌙 Starting memory consolidation cycle...")

        # 1. Retrieve recent episodic memories
        memories = self.episodic.get_recent(n=max_memories, session_id=session_id)

        if not memories:
            logger.info("No memories to consolidate.")
            return {"processed": 0, "entities_extracted": 0, "relationships_extracted": 0}

        # 2. Group into conversation pairs (user + assistant)
        conversations = self._pair_conversations(memories)
        logger.info(f"Found {len(conversations)} conversation pairs to process")

        total_entities = 0
        total_relationships = 0

        # 3. Extract entities and relationships from each pair
        for conv in conversations:
            try:
                result = await extract_entities(conv["text"])

                # 4. Add entities to knowledge graph
                for entity in result.get("entities", []):
                    self.knowledge_graph.add_entity(
                        name=entity.get("name", ""),
                        entity_type=entity.get("type", "concept"),
                        source="consolidation",
                    )
                    total_entities += 1

                # 5. Add relationships to knowledge graph
                for rel in result.get("relationships", []):
                    self.knowledge_graph.add_relationship(
                        source_name=rel.get("source", ""),
                        target_name=rel.get("target", ""),
                        relation=rel.get("relation", "related_to"),
                        context=conv["text"][:200],
                    )
                    total_relationships += 1

            except Exception as e:
                logger.error(f"Consolidation failed for a conversation pair: {e}")
                continue

        summary = {
            "processed": len(conversations),
            "entities_extracted": total_entities,
            "relationships_extracted": total_relationships,
            "graph_stats": self.knowledge_graph.get_stats(),
        }

        logger.info(
            f"🌙 Consolidation complete: {total_entities} entities, "
            f"{total_relationships} relationships extracted from "
            f"{len(conversations)} conversations"
        )

        return summary

    async def generate_reflection(self, session_id: Optional[str] = None) -> str:
        """
        Generate a self-reflection summary of recent interactions.

        Inspired by the blueprint's Self-Reflection Loop:
        'What went well? What was suboptimal?'

        Returns:
            Reflection text.
        """
        memories = self.episodic.get_recent(n=20, session_id=session_id)
        if not memories:
            return "No recent interactions to reflect on."

        # Build conversation summary
        summary_parts = []
        for mem in reversed(memories):
            role = mem.get("metadata", {}).get("role", "unknown")
            content = mem.get("content", "")[:150]
            summary_parts.append(f"({role}): {content}")

        conversation_summary = "\n".join(summary_parts)

        # Use LLM for reflection
        try:
            import ollama
            from backend.app.config import get_settings

            settings = get_settings()
            client = ollama.AsyncClient(host=settings.ollama_host)

            response = await client.chat(
                model=settings.ollama_model,
                messages=[{
                    "role": "user",
                    "content": f"""Review this recent conversation and generate a brief reflection:

{conversation_summary}

Reflect on:
1. What topics were discussed?
2. What did you learn about the user?
3. What could be improved in future interactions?
4. Any patterns or preferences noticed?

Keep it concise (3-5 sentences)."""
                }],
                options={"temperature": 0.3},
            )

            return response.message.content

        except Exception as e:
            logger.error(f"Reflection generation failed: {e}")
            return f"Reflection unavailable: {e}"

    def _pair_conversations(self, memories: list[dict]) -> list[dict]:
        """Group memories into user-assistant conversation pairs."""
        # Sort chronologically
        sorted_mems = sorted(
            memories,
            key=lambda m: m.get("metadata", {}).get("timestamp", ""),
        )

        pairs = []
        i = 0
        while i < len(sorted_mems) - 1:
            current = sorted_mems[i]
            next_mem = sorted_mems[i + 1]

            cur_role = current.get("metadata", {}).get("role", "")
            next_role = next_mem.get("metadata", {}).get("role", "")

            if cur_role == "user" and next_role == "assistant":
                pairs.append({
                    "text": extract_user_facts(
                        current.get("content", ""),
                        next_mem.get("content", ""),
                    ),
                    "session_id": current.get("metadata", {}).get("session_id", ""),
                    "timestamp": current.get("metadata", {}).get("timestamp", ""),
                })
                i += 2
            else:
                i += 1

        return pairs

    def get_stats(self) -> dict:
        """Get consolidation system stats."""
        return {
            "episodic_memories": self.episodic.get_stats(),
            "knowledge_graph": self.knowledge_graph.get_stats(),
        }
