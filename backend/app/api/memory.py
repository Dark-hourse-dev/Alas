"""
ALAS Memory API — Endpoints for memory inspection and management.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.memory.retrieval import MemoryRetriever

router = APIRouter(prefix="/api/memory", tags=["memory"])

_retriever: Optional[MemoryRetriever] = None


def get_retriever() -> MemoryRetriever:
    global _retriever
    if _retriever is None:
        _retriever = MemoryRetriever()
    return _retriever


class MemorySearchRequest(BaseModel):
    query: str
    n_results: int = 5
    mode: Optional[str] = None


class MemorySearchResponse(BaseModel):
    memories: list[dict]
    total_count: int


@router.get("/stats")
async def memory_stats():
    """Get memory system statistics."""
    retriever = get_retriever()
    return retriever.get_memory_stats()


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(request: MemorySearchRequest):
    """Search episodic memories by semantic similarity."""
    retriever = get_retriever()
    memories = retriever.episodic.recall(
        query=request.query,
        n_results=request.n_results,
        mode_filter=request.mode,
    )
    stats = retriever.episodic.get_stats()
    return MemorySearchResponse(
        memories=memories,
        total_count=stats["total_memories"],
    )


@router.get("/recent")
async def recent_memories(n: int = 20, session_id: Optional[str] = None):
    """Get most recent memories."""
    retriever = get_retriever()
    memories = retriever.episodic.get_recent(n=n, session_id=session_id)
    return {"memories": memories}


@router.get("/sessions")
async def get_sessions(limit: int = 50):
    """Get a list of unique chat sessions and their latest activity."""
    retriever = get_retriever()
    sessions = retriever.episodic.get_sessions(limit=limit)
    return {"sessions": sessions}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory entry."""
    retriever = get_retriever()
    retriever.episodic.delete(memory_id)
    return {"status": "deleted", "memory_id": memory_id}


@router.delete("/")
async def clear_memories():
    """Clear ALL episodic memories. Irreversible."""
    retriever = get_retriever()
    retriever.episodic.clear_all()
    return {"status": "cleared"}


class FeedbackRequest(BaseModel):
    message_content: str
    feedback_type: str  # 'positive' or 'negative'
    session_id: str
    correction: Optional[str] = None

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit implicit feedback (thumbs up/down) for future model fine-tuning (LoRA).
    Stores feedback in a JSONL file in the data directory.
    """
    import json
    import time
    from pathlib import Path
    
    data_dir = Path("backend/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = data_dir / "feedback.jsonl"
    
    feedback_entry = {
        "timestamp": time.time(),
        "session_id": request.session_id,
        "message_content": request.message_content,
        "feedback": request.feedback_type,
        "correction": request.correction
    }
    
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
