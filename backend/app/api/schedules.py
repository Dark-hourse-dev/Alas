"""
ALAS Schedules API — User-defined recurring automations.

CRUD endpoints for scheduled jobs:
  "Every Monday, summarize my git commits for the week."
  "Every morning at 8, tell me the weather."
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.proactive.scheduler import get_scheduler

logger = logging.getLogger("alas.api.schedules")
router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    name: str
    description: str = ""
    schedule_type: str = "interval"  # "interval" or "cron"
    interval_minutes: Optional[int] = None  # For interval type
    cron_expression: Optional[str] = None  # For cron type (e.g., "0 8 * * 1" = Monday 8AM)
    action_type: str = "reminder"  # "reminder", "shell", "research"
    action_params: dict = {}  # Parameters for the action


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    interval_minutes: Optional[int] = None
    cron_expression: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
async def list_schedules():
    """List all user-defined schedules."""
    scheduler = get_scheduler()
    tasks = scheduler.get_tasks()
    return {
        "schedules": [
            t for t in tasks
            if t.get("type") in ("recurring", "user_schedule")
        ],
        "total": len(tasks),
    }


@router.post("")
async def create_schedule(request: ScheduleCreate):
    """Create a new recurring schedule."""
    scheduler = get_scheduler()

    if request.schedule_type == "interval" and not request.interval_minutes:
        raise HTTPException(400, "interval_minutes is required for interval schedules.")
    if request.schedule_type == "cron" and not request.cron_expression:
        raise HTTPException(400, "cron_expression is required for cron schedules.")

    # Register the callback based on action type
    callback_name = f"user_schedule_{request.name.lower().replace(' ', '_')}"

    # Create the callback function
    if request.action_type == "reminder":
        message = request.action_params.get("message", request.description or request.name)

        async def callback():
            from backend.app.proactive.notifier import get_notifier
            get_notifier().send(
                title=f"📅 {request.name}",
                message=message,
            )

    elif request.action_type == "shell":
        command = request.action_params.get("command", "echo 'No command specified'")

        async def callback():
            from backend.app.llm.tools import execute_shell
            result = execute_shell(command)
            from backend.app.proactive.notifier import get_notifier
            get_notifier().send(
                title=f"📅 {request.name}",
                message=f"Executed: {command}\nResult: {result[:200]}",
            )

    elif request.action_type == "research":
        topic = request.action_params.get("topic", request.name)

        async def callback():
            from backend.app.tools.research_agent import research_topic
            result = research_topic(topic=topic, depth="quick")
            from backend.app.proactive.notifier import get_notifier
            get_notifier().send(
                title=f"🔬 Research: {topic}",
                message=f"Research complete. {len(result)} chars generated.",
            )

    else:
        raise HTTPException(400, f"Unknown action_type: {request.action_type}")

    scheduler.register_callback(callback_name, callback)

    task_id = scheduler.add_recurring(
        name=request.name,
        callback_name=callback_name,
        interval_minutes=request.interval_minutes,
        cron_expression=request.cron_expression,
    )

    return {
        "id": task_id,
        "name": request.name,
        "status": "active",
        "message": f"Schedule '{request.name}' created successfully.",
    }


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a scheduled job."""
    scheduler = get_scheduler()
    success = scheduler.cancel_task(schedule_id)

    if success:
        return {"message": f"Schedule {schedule_id} deleted."}
    else:
        raise HTTPException(404, f"Schedule {schedule_id} not found.")


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    """Get details of a specific schedule."""
    scheduler = get_scheduler()
    tasks = scheduler.get_tasks()

    for task in tasks:
        if task.get("id") == schedule_id:
            return task

    raise HTTPException(404, f"Schedule {schedule_id} not found.")
