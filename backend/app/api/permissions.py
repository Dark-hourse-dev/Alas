"""
ALAS Permissions API — Manage the Permission Tier System.

Endpoints for viewing action history, managing user overrides,
classifying commands, and approving pending requests.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.safety.permissions import get_permission_manager

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


class OverrideRequest(BaseModel):
    pattern: str
    tier: str  # "auto", "notify", or "ask"


class ClassifyRequest(BaseModel):
    command: str


# --- Endpoints ---

@router.get("/actions")
async def get_action_history(limit: int = 30):
    """Get the recent action audit log."""
    pm = get_permission_manager()
    return {"actions": pm.get_recent_actions(limit)}


@router.get("/overrides")
async def get_overrides():
    """Get all user-defined permission overrides."""
    pm = get_permission_manager()
    return {"overrides": pm.get_overrides()}


@router.post("/overrides")
async def add_override(req: OverrideRequest):
    """Add a permanent permission override for a command pattern."""
    pm = get_permission_manager()
    try:
        pm.add_override(req.pattern, req.tier)
        return {"status": "success", "pattern": req.pattern, "tier": req.tier}
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@router.delete("/overrides/{pattern}")
async def remove_override(pattern: str):
    """Remove a user-defined permission override."""
    pm = get_permission_manager()
    pm.remove_override(pattern)
    return {"status": "success"}


@router.post("/classify")
async def classify_command(req: ClassifyRequest):
    """
    Preview how a command would be classified without executing it.
    Useful for the frontend permissions panel.
    """
    pm = get_permission_manager()
    tier, reason = pm.classify_command(req.command)
    return {
        "command": req.command,
        "tier": tier.value,
        "reason": reason,
        "icon": {"auto": "🟢", "notify": "🟡", "ask": "🔴"}.get(tier.value, "❓"),
    }


@router.get("/summary")
async def permission_summary():
    """
    Get a summary of the permission system status.
    """
    pm = get_permission_manager()
    actions = pm.get_recent_actions(100)

    total = len(actions)
    blocked = sum(1 for a in actions if a.get("result") == "BLOCKED")
    auto_count = sum(1 for a in actions if a.get("tier") == "auto")
    notify_count = sum(1 for a in actions if a.get("tier") == "notify")

    return {
        "total_actions": total,
        "auto_approved": auto_count,
        "notify_executed": notify_count,
        "blocked": blocked,
        "user_overrides": len(pm.get_overrides()),
    }
