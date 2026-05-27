"""
ALAS Tasks API.

Endpoints for managing scheduled reminders and recurring tasks.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.proactive.scheduler import get_scheduler

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class ReminderRequest(BaseModel):
    message: str
    run_at: datetime
    
class RecurringRequest(BaseModel):
    name: str
    callback_name: str
    interval_minutes: int = None
    cron_expression: str = None

@router.get("/")
async def list_tasks():
    """Get all scheduled tasks."""
    return {"tasks": get_scheduler().get_tasks()}

@router.post("/reminders")
async def create_reminder(req: ReminderRequest):
    """Create a one-time reminder."""
    try:
        task_id = get_scheduler().add_reminder(req.message, req.run_at)
        return {"status": "success", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/recurring")
async def create_recurring(req: RecurringRequest):
    """Create a recurring task."""
    try:
        task_id = get_scheduler().add_recurring(
            req.name, req.callback_name, req.interval_minutes, req.cron_expression
        )
        return {"status": "success", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a task."""
    success = get_scheduler().cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success"}
