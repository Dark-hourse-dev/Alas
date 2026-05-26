"""
ALAS Memory Retrieval Pipeline — RAG-style context composition.

Implements the full retrieval pipeline:
  User input → Embed → Similarity search L1 → Graph query L2 → Load profile L3 → Compose context
"""

from typing import Optional

from backend.app.memory.episodic import EpisodicMemory
from backend.app.memory.profile import ProfileStore
from backend.app.memory.knowledge_graph import KnowledgeGraph


class MemoryRetriever:
    """
    Unified memory retrieval pipeline that combines episodic
    memory search with user profile context to compose rich
    context windows for LLM inference.
    """

    def __init__(self):
        self.episodic = EpisodicMemory()
        self.profile_store = ProfileStore()
        self.knowledge_graph = KnowledgeGraph()

    def retrieve_context(
        self,
        query: str,
        session_id: Optional[str] = None,
        mode: Optional[str] = None,
        n_memories: int = 5,
        user_id: str = "default",
    ) -> dict:
        """
        Full retrieval pipeline: search episodic memory + load profile.
        
        Args:
            query: The user's current input.
            session_id: Current session identifier.
            mode: Current interaction mode filter.
            n_memories: Number of episodic memories to retrieve.
            user_id: User identifier.
            
        Returns:
            Dictionary with:
              - relevant_memories: list of similar past interactions
              - recent_context: recent messages from this session
              - user_profile: current user profile data
              - composed_context: formatted string for LLM prompt
        """
        # 1. Similarity search in episodic memory
        relevant_memories = self.episodic.recall(
            query=query,
            n_results=n_memories,
            mode_filter=mode,
        )

        # 2. Get recent session context
        recent_context = []
        if session_id:
            recent_context = self.episodic.get_recent(
                n=10,
                session_id=session_id,
            )

        # 3. Load user profile
        user_profile = self.profile_store.get_profile(user_id)

        # 4. Query knowledge graph for related concepts
        kg_context = self.knowledge_graph.get_context_for_query(query, limit=5)

        # 5. Compose context string for LLM
        composed_context = self._compose_context(
            relevant_memories=relevant_memories,
            recent_context=recent_context,
            user_profile=user_profile,
            kg_context=kg_context,
        )

        return {
            "relevant_memories": relevant_memories,
            "recent_context": recent_context,
            "user_profile": user_profile,
            "kg_context": kg_context,
            "composed_context": composed_context,
        }

    def _compose_context(
        self,
        relevant_memories: list[dict],
        recent_context: list[dict],
        user_profile: dict,
        kg_context: str = "",
    ) -> str:
        """Format retrieved context into a structured string for LLM prompt injection."""
        parts = []

        # User profile section
        name = user_profile.get("preferred_name") or user_profile.get("name")
        if name:
            parts.append(f"[User: {name}]")

        style = user_profile.get("communication_style", "balanced")
        parts.append(f"[Communication style: {style}]")

        topics = user_profile.get("topics_of_interest", [])
        if topics:
            parts.append(f"[Known interests: {', '.join(topics[:10])}]")

        interaction_count = user_profile.get("interaction_count", 0)
        if interaction_count > 0:
            parts.append(f"[Total interactions: {interaction_count}]")

        # Knowledge graph context (L2)
        if kg_context:
            parts.append(f"\n{kg_context}")

        # Relevant memories section
        if relevant_memories:
            parts.append("\n--- Relevant Past Memories ---")
            for mem in relevant_memories[:5]:
                ts = mem.get("metadata", {}).get("timestamp", "unknown time")
                role = mem.get("metadata", {}).get("role", "unknown")
                content = mem.get("content", "")
                # Truncate long memories
                if len(content) > 300:
                    content = content[:300] + "..."
                parts.append(f"[{ts}] ({role}): {content}")

        # Recent conversation context
        if recent_context:
            parts.append("\n--- Recent Conversation ---")
            # Show in chronological order (reverse since stored desc)
            for msg in reversed(recent_context[:8]):
                role = msg.get("metadata", {}).get("role", "unknown")
                content = msg.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                parts.append(f"({role}): {content}")

        return "\n".join(parts)

    def store_interaction(
        self,
        content: str,
        role: str = "user",
        mode: str = "casual",
        session_id: Optional[str] = None,
        emotion: Optional[str] = None,
        user_id: str = "default",
    ) -> str:
        """
        Store a new interaction in episodic memory and update profile.
        
        Args:
            content: Message content.
            role: 'user' or 'assistant'.
            mode: Current interaction mode.
            session_id: Session identifier.
            emotion: Detected emotion (optional).
            user_id: User identifier.
            
        Returns:
            The memory entry ID.
        """
        memory_id = self.episodic.store(
            content=content,
            role=role,
            mode=mode,
            emotion=emotion,
            session_id=session_id,
        )

        # Increment interaction count for the user
        if role == "user":
            self.profile_store.increment_interaction(user_id)

        return memory_id

    def get_memory_stats(self) -> dict:
        """Get combined memory statistics."""
        episodic_stats = self.episodic.get_stats()
        return {
            "episodic": episodic_stats,
        }
