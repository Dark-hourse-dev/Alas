"""
ALAS Tasks API — Scheduled reminders, recurring tasks, and background task queue.

Endpoints for:
- Managing scheduled reminders and recurring tasks (scheduler)
- Submitting and monitoring background tasks (queue)
- Viewing task history and results
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.proactive.scheduler import get_scheduler

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# --- Models ---

class ReminderRequest(BaseModel):
    message: str
    run_at: datetime


class RecurringRequest(BaseModel):
    name: str
    callback_name: str
    interval_minutes: int = None
    cron_expression: str = None


class BackgroundTaskRequest(BaseModel):
    name: str
    task_type: str  # "research", "code_exec"
    description: str = ""
    params: dict = {}


# --- Scheduler Endpoints (reminders + recurring) ---

@router.get("/")
async def list_tasks():
    """Get all scheduled tasks and background tasks."""
    from backend.app.tasks.queue import get_task_queue

    scheduler_tasks = get_scheduler().get_tasks()
    queue_tasks = get_task_queue().get_all_tasks(limit=50)

    return {
        "scheduled_tasks": scheduler_tasks,
        "background_tasks": queue_tasks,
        "total_scheduled": len(scheduler_tasks),
        "total_background": len(queue_tasks),
    }


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
    """Cancel a scheduled or background task."""
    # Try scheduler first
    if get_scheduler().cancel_task(task_id):
        return {"status": "success", "source": "scheduler"}

    # Try background queue
    from backend.app.tasks.queue import get_task_queue
    if get_task_queue().cancel_task(task_id):
        return {"status": "success", "source": "queue"}

    raise HTTPException(status_code=404, detail="Task not found")


# --- Background Queue Endpoints ---

@router.post("/submit")
async def submit_background_task(req: BackgroundTaskRequest):
    """Submit a new background task to the queue."""
    from backend.app.tasks.queue import get_task_queue

    queue = get_task_queue()
    task_id = queue.submit(
        name=req.name,
        task_type=req.task_type,
        description=req.description,
        params=req.params,
    )

    return {
        "status": "submitted",
        "task_id": task_id,
        "name": req.name,
        "task_type": req.task_type,
    }


@router.get("/queue")
async def list_queue():
    """Get all background tasks (active + history)."""
    from backend.app.tasks.queue import get_task_queue

    queue = get_task_queue()
    return {
        "active": queue.get_active_tasks(),
        "all": queue.get_all_tasks(limit=50),
    }


@router.get("/queue/active")
async def list_active_tasks():
    """Get only active (pending + running) background tasks."""
    from backend.app.tasks.queue import get_task_queue

    return {"active_tasks": get_task_queue().get_active_tasks()}


@router.get("/queue/{task_id}")
async def get_background_task(task_id: str):
    """Get the status and result of a specific background task."""
    from backend.app.tasks.queue import get_task_queue

    task = get_task_queue().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return task


# --- Plans Endpoints ---

@router.get("/plans")
async def list_plans():
    """Get all execution plans."""
    from backend.app.planning.executor import get_all_plans
    return {"plans": get_all_plans()}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get details of a specific plan."""
    from backend.app.planning.executor import get_plan
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found.")
    return plan.to_dict()


@router.post("/plans/{plan_id}/execute")
async def execute_plan_endpoint(plan_id: str):
    """Execute an approved plan."""
    from backend.app.planning.executor import get_plan, execute_plan

    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found.")

    if plan.status not in ("draft", "approved"):
        raise HTTPException(
            status_code=400,
            detail=f"Plan is in '{plan.status}' state. Only 'draft' or 'approved' plans can be executed."
        )

    result = await execute_plan(plan)
    return result.to_dict()
