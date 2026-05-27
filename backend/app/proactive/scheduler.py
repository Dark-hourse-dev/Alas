"""
ALAS Scheduler — APScheduler-based task engine.

Manages scheduled tasks, reminders, and recurring jobs.
Persists tasks to disk so they survive restarts.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.app.config import get_settings

logger = logging.getLogger("alas.proactive.scheduler")


class ALASScheduler:
    """Central task scheduler for ALAS proactive features."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        self._data_dir = Path(get_settings().chroma_persist_dir).parent / "scheduler"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._tasks_file = self._data_dir / "tasks.json"
        self._tasks: dict = self._load_tasks()
        self._callbacks: dict[str, Callable] = {}
        self._started = False

    def start(self):
        """Start the scheduler (call once at app startup)."""
        if self._started:
            return
        self._scheduler.start()
        self._started = True
        self._restore_tasks()
        logger.info(f"⏰ Scheduler started with {len(self._tasks)} saved tasks")

    def shutdown(self):
        """Gracefully shut down."""
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    # --- Task Management ---

    def add_reminder(
        self,
        message: str,
        run_at: datetime,
        user_id: str = "default",
    ) -> str:
        """Schedule a one-time reminder."""
        task_id = f"rem_{uuid.uuid4().hex[:8]}"

        self._tasks[task_id] = {
            "id": task_id,
            "type": "reminder",
            "message": message,
            "run_at": run_at.isoformat(),
            "user_id": user_id,
            "created": datetime.now().isoformat(),
            "status": "scheduled",
        }

        if self._started:
            self._scheduler.add_job(
                self._fire_reminder,
                trigger=DateTrigger(run_date=run_at),
                id=task_id,
                args=[task_id, message],
                replace_existing=True,
            )

        self._save_tasks()
        logger.info(f"⏰ Reminder scheduled: '{message}' at {run_at}")
        return task_id

    def add_recurring(
        self,
        name: str,
        callback_name: str,
        interval_minutes: Optional[int] = None,
        cron_expression: Optional[str] = None,
    ) -> str:
        """Schedule a recurring task."""
        task_id = f"rec_{uuid.uuid4().hex[:8]}"

        self._tasks[task_id] = {
            "id": task_id,
            "type": "recurring",
            "name": name,
            "callback": callback_name,
            "interval_minutes": interval_minutes,
            "cron": cron_expression,
            "created": datetime.now().isoformat(),
            "status": "active",
        }

        if self._started:
            self._schedule_recurring(task_id)

        self._save_tasks()
        logger.info(f"⏰ Recurring task registered: '{name}'")
        return task_id

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "cancelled"
            try:
                self._scheduler.remove_job(task_id)
            except Exception:
                pass
            self._save_tasks()
            logger.info(f"⏰ Task cancelled: {task_id}")
            return True
        return False

    def get_tasks(self) -> list[dict]:
        """Get all scheduled tasks."""
        return [t for t in self._tasks.values() if t["status"] != "cancelled"]

    def get_pending_reminders(self) -> list[dict]:
        """Get reminders that haven't fired yet."""
        now = datetime.now()
        return [
            t for t in self._tasks.values()
            if t["type"] == "reminder"
            and t["status"] == "scheduled"
            and datetime.fromisoformat(t["run_at"]) > now
        ]

    # --- Callback Registration ---

    def register_callback(self, name: str, fn: Callable):
        """Register a named callback for recurring tasks."""
        self._callbacks[name] = fn
        logger.debug(f"Registered scheduler callback: {name}")

    # --- Internal ---

    async def _fire_reminder(self, task_id: str, message: str):
        """Fire a reminder notification."""
        logger.info(f"🔔 Reminder fired: {message}")
        self._tasks[task_id]["status"] = "completed"
        self._save_tasks()

        # Send desktop notification
        from backend.app.proactive.notifier import get_notifier
        get_notifier().send(
            title="⏰ ALAS Reminder",
            message=message,
            urgency="normal",
        )

    def _schedule_recurring(self, task_id: str):
        """Schedule a recurring job from task data."""
        task = self._tasks[task_id]
        callback_name = task.get("callback")
        callback = self._callbacks.get(callback_name)

        if not callback:
            logger.warning(f"No callback registered for '{callback_name}', skipping task {task_id}")
            return

        if task.get("cron"):
            parts = task["cron"].split()
            trigger = CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
            )
        elif task.get("interval_minutes"):
            trigger = IntervalTrigger(minutes=task["interval_minutes"])
        else:
            return

        self._scheduler.add_job(
            callback,
            trigger=trigger,
            id=task_id,
            replace_existing=True,
        )

    def _restore_tasks(self):
        """Restore saved tasks on startup."""
        now = datetime.now()
        for task_id, task in list(self._tasks.items()):
            if task["status"] == "cancelled":
                continue

            if task["type"] == "reminder" and task["status"] == "scheduled":
                run_at = datetime.fromisoformat(task["run_at"])
                if run_at > now:
                    self._scheduler.add_job(
                        self._fire_reminder,
                        trigger=DateTrigger(run_date=run_at),
                        id=task_id,
                        args=[task_id, task["message"]],
                        replace_existing=True,
                    )
                else:
                    task["status"] = "expired"

            elif task["type"] == "recurring" and task["status"] == "active":
                self._schedule_recurring(task_id)

        self._save_tasks()

    def _load_tasks(self) -> dict:
        if self._tasks_file.exists():
            try:
                return json.loads(self._tasks_file.read_text())
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
        return {}

    def _save_tasks(self):
        self._tasks_file.write_text(json.dumps(self._tasks, indent=2, default=str))


# Singleton
_scheduler: Optional[ALASScheduler] = None


def get_scheduler() -> ALASScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ALASScheduler()
    return _scheduler
