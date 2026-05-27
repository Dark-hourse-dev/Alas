"""
ALAS Task Queue — Async background task execution engine.

Manages long-running tasks that execute asynchronously:
- Research jobs
- File processing
- Code analysis
- Plan execution

Tasks persist to disk and report progress via callbacks.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field, asdict

from backend.app.config import get_settings

logger = logging.getLogger("alas.tasks.queue")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """A background task in the queue."""
    id: str
    name: str
    description: str
    task_type: str  # "research", "code_exec", "plan", "custom"
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    progress_message: str = ""
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# Type for task handler functions
TaskHandler = Callable[[BackgroundTask, Callable], Awaitable[str]]


class TaskQueue:
    """In-memory async task queue with disk persistence."""

    def __init__(self):
        self._data_dir = Path(get_settings().chroma_persist_dir).parent / "tasks"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._tasks_file = self._data_dir / "task_history.json"

        self._tasks: dict[str, BackgroundTask] = {}
        self._handlers: dict[str, TaskHandler] = {}
        self._on_complete_callbacks: list[Callable] = []
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

        # Load completed tasks from history
        self._load_history()

        # Register built-in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register handlers for built-in task types."""
        self.register_handler("research", self._handle_research)
        self.register_handler("code_exec", self._handle_code_exec)

    def register_handler(self, task_type: str, handler: TaskHandler):
        """Register a handler function for a task type."""
        self._handlers[task_type] = handler
        logger.debug(f"Registered task handler: {task_type}")

    def on_complete(self, callback: Callable):
        """Register a callback for task completion (for WebSocket notifications)."""
        self._on_complete_callbacks.append(callback)

    async def start_worker(self):
        """Start the background worker loop."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("📋 Task queue worker started")

    async def stop_worker(self):
        """Stop the background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("📋 Task queue worker stopped")

    def submit(
        self,
        name: str,
        task_type: str,
        description: str = "",
        params: Optional[dict] = None,
    ) -> str:
        """
        Submit a new background task.

        Args:
            name: Human-readable task name.
            task_type: Type of task (must have a registered handler).
            description: Description of what the task will do.
            params: Parameters to pass to the handler.

        Returns:
            Task ID.
        """
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        task = BackgroundTask(
            id=task_id,
            name=name,
            description=description,
            task_type=task_type,
            params=params or {},
        )
        self._tasks[task_id] = task

        # Put in the async queue
        try:
            self._queue.put_nowait(task_id)
        except asyncio.QueueFull:
            task.status = TaskStatus.FAILED
            task.error = "Task queue is full. Try again later."
            return task_id

        logger.info(f"📋 Task submitted: {name} ({task_type}) → {task_id}")
        self._save_history()
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get task status and details."""
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None

    def get_active_tasks(self) -> list[dict]:
        """Get all active (pending + running) tasks."""
        return [
            t.to_dict() for t in self._tasks.values()
            if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]

    def get_all_tasks(self, limit: int = 50) -> list[dict]:
        """Get all tasks, most recent first."""
        sorted_tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )
        return [t.to_dict() for t in sorted_tasks[:limit]]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task (cannot cancel running tasks)."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().isoformat()
            self._save_history()
            logger.info(f"📋 Task cancelled: {task_id}")
            return True
        return False

    # --- Worker Loop ---

    async def _worker_loop(self):
        """Background worker that processes tasks from the queue."""
        while self._running:
            try:
                task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            task = self._tasks.get(task_id)
            if not task or task.status == TaskStatus.CANCELLED:
                continue

            handler = self._handlers.get(task.task_type)
            if not handler:
                task.status = TaskStatus.FAILED
                task.error = f"No handler registered for task type: {task.task_type}"
                task.completed_at = datetime.now().isoformat()
                self._save_history()
                continue

            # Execute the task
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._save_history()

            logger.info(f"📋 Executing task: {task.name} ({task_id})")

            try:
                def update_progress(progress: float, message: str = ""):
                    task.progress = min(progress, 1.0)
                    task.progress_message = message

                result = await handler(task, update_progress)

                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 1.0
                task.progress_message = "Complete"
                task.completed_at = datetime.now().isoformat()

                logger.info(f"✅ Task completed: {task.name} ({task_id})")

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now().isoformat()
                logger.error(f"❌ Task failed: {task.name} ({task_id}): {e}")

            self._save_history()

            # Notify completion callbacks
            for cb in self._on_complete_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(task.to_dict())
                    else:
                        cb(task.to_dict())
                except Exception as e:
                    logger.error(f"Task completion callback error: {e}")

    # --- Built-in Handlers ---

    async def _handle_research(self, task: BackgroundTask, update_progress: Callable) -> str:
        """Handle a research task."""
        from backend.app.tools.research_agent import research_topic

        topic = task.params.get("topic", "")
        depth = task.params.get("depth", "standard")

        if not topic:
            raise ValueError("Research topic is required.")

        update_progress(0.1, "Starting research...")

        # Run in thread pool since research_topic is synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: research_topic(topic=topic, depth=depth),
        )

        update_progress(1.0, "Research complete")
        return result

    async def _handle_code_exec(self, task: BackgroundTask, update_progress: Callable) -> str:
        """Handle a code execution task."""
        from backend.app.sandbox.executor import run_code

        code = task.params.get("code", "")
        language = task.params.get("language", "python")

        if not code:
            raise ValueError("Code is required.")

        update_progress(0.2, f"Executing {language} code...")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_code(code=code, language=language),
        )

        update_progress(1.0, "Execution complete")
        return result.to_str()

    # --- Persistence ---

    def _save_history(self):
        """Save task history to disk."""
        try:
            data = {
                tid: t.to_dict()
                for tid, t in self._tasks.items()
            }
            self._tasks_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save task history: {e}")

    def _load_history(self):
        """Load completed tasks from history file."""
        if not self._tasks_file.exists():
            return
        try:
            data = json.loads(self._tasks_file.read_text())
            for tid, tdata in data.items():
                # Only load completed/failed tasks for history
                status = tdata.get("status", "completed")
                if status in ("completed", "failed", "cancelled"):
                    self._tasks[tid] = BackgroundTask(
                        id=tid,
                        name=tdata.get("name", ""),
                        description=tdata.get("description", ""),
                        task_type=tdata.get("task_type", "custom"),
                        status=TaskStatus(status),
                        result=tdata.get("result"),
                        error=tdata.get("error"),
                        created_at=tdata.get("created_at", ""),
                        completed_at=tdata.get("completed_at"),
                    )
            logger.info(f"📋 Loaded {len(self._tasks)} tasks from history")
        except Exception as e:
            logger.error(f"Failed to load task history: {e}")


# --- Singleton ---
_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get the global task queue singleton."""
    global _queue
    if _queue is None:
        _queue = TaskQueue()
    return _queue
