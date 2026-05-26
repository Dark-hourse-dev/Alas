"""
ALAS Profile API — User profile management endpoints.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.memory.profile import ProfileStore

router = APIRouter(prefix="/api/profile", tags=["profile"])

_store: Optional[ProfileStore] = None


def get_store() -> ProfileStore:
    global _store
    if _store is None:
        _store = ProfileStore()
    return _store


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    preferred_name: Optional[str] = None
    communication_style: Optional[str] = None
    preferred_mode: Optional[str] = None
    topics_of_interest: Optional[list[str]] = None
    emotional_baseline: Optional[str] = None
    timezone: Optional[str] = None


@router.get("/{user_id}")
async def get_profile(user_id: str = "default"):
    """Get user profile."""
    store = get_store()
    return store.get_profile(user_id)


@router.put("/{user_id}")
async def update_profile(user_id: str, request: ProfileUpdateRequest):
    """Update user profile fields."""
    store = get_store()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    return store.update_profile(user_id, **updates)


@router.get("/{user_id}/history")
async def get_interaction_history(user_id: str = "default", limit: int = 50):
    """Get interaction session history."""
    store = get_store()
    return {"history": store.get_interaction_history(user_id, limit)}
