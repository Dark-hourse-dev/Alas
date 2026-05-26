"""
ALAS Episodic Memory (L1) — ChromaDB-backed vector memory.

Stores all interactions as dense embeddings with metadata for
time, context, mode, and relevance scoring. Supports similarity
search for RAG-style memory retrieval.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.app.config import get_settings


class EpisodicMemory:
    """
    Layer 1 — Episodic Memory.
    
    Stores time-stamped interaction events as vector embeddings
    in ChromaDB. Supports similarity search for retrieving
    relevant past conversations.
    """

    def __init__(self):
        settings = get_settings()
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Main conversation memory collection
        self._collection = self._client.get_or_create_collection(
            name="episodic_memory",
            metadata={"hnsw:space": "cosine"},
        )

    def store(
        self,
        content: str,
        role: str = "user",
        mode: str = "casual",
        emotion: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a new memory entry.
        
        Args:
            content: The text content to store.
            role: 'user' or 'assistant'.
            mode: Current interaction mode (work, casual, etc.).
            emotion: Detected emotional state (optional).
            session_id: Conversation session identifier.
            metadata: Additional metadata to attach.
            
        Returns:
            The generated memory ID.
        """
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        doc_metadata = {
            "role": role,
            "mode": mode,
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "session_id": session_id or "default",
        }
        if emotion:
            doc_metadata["emotion"] = emotion
        if metadata:
            doc_metadata.update(metadata)

        self._collection.add(
            ids=[memory_id],
            documents=[content],
            metadatas=[doc_metadata],
        )
        return memory_id

    def recall(
        self,
        query: str,
        n_results: int = 5,
        mode_filter: Optional[str] = None,
        time_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve relevant memories via similarity search.
        
        Args:
            query: The search query text.
            n_results: Number of results to return.
            mode_filter: Filter by interaction mode.
            time_filter: Filter by date (YYYY-MM-DD).
            
        Returns:
            List of memory entries with content, metadata, and distance.
        """
        where_filter = {}
        if mode_filter:
            where_filter["mode"] = mode_filter
        if time_filter:
            where_filter["date"] = time_filter

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, get_settings().max_memory_results),
            where=where_filter if where_filter else None,
        )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "id": results["ids"][0][i],
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return memories

    def get_recent(self, n: int = 20, session_id: Optional[str] = None) -> list[dict]:
        """
        Get the most recent memories, optionally filtered by session.
        
        Args:
            n: Number of recent entries to return.
            session_id: Optional session filter.
            
        Returns:
            List of memory entries sorted by recency.
        """
        where_filter = None
        if session_id:
            where_filter = {"session_id": session_id}

        results = self._collection.get(
            where=where_filter,
            limit=n,
            include=["documents", "metadatas"],
        )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                memories.append({
                    "id": results["ids"][i],
                    "content": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
            # Sort by timestamp descending
            memories.sort(
                key=lambda m: m["metadata"].get("timestamp", ""),
                reverse=True,
            )
        return memories

    def get_stats(self) -> dict:
        """Get memory statistics."""
        count = self._collection.count()
        return {
            "total_memories": count,
            "collection_name": "episodic_memory",
        }

    def delete(self, memory_id: str):
        """Delete a specific memory entry."""
        self._collection.delete(ids=[memory_id])

    def clear_all(self):
        """Clear all episodic memories. Use with caution."""
        self._client.delete_collection("episodic_memory")
        self._collection = self._client.get_or_create_collection(
            name="episodic_memory",
            metadata={"hnsw:space": "cosine"},
        )
