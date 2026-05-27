"""
ALAS — Main Application Entry Point.

FastAPI server with WebSocket support, CORS, static file serving,
and all API routes mounted.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import get_settings, ensure_data_dirs
from backend.app.api import chat, memory, profile, voice, knowledge, sync, learning, permissions, tasks, schedules
from backend.app.proactive.scheduler import get_scheduler
from backend.app.proactive.monitors import register_monitors

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alas")


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI): 
    """Application startup and shutdown lifecycle."""
    logger.info("🧬 ALAS — Adaptive Living AI System starting up...")
    ensure_data_dirs()
    settings = get_settings()
    logger.info(f"   Model: {settings.ollama_model}")
    logger.info(f"   Ollama: {settings.ollama_host}")
    logger.info(f"   Memory: ChromaDB @ {settings.chroma_persist_dir}")
    logger.info(f"   Profile: SQLite @ {settings.sqlite_db_path}")
    logger.info(f"   Knowledge Graph: NetworkX (persistent JSON)")
    logger.info(f"   Emotion Detection: Active")
    logger.info(f"   Permission Tiers: 🟢 AUTO / 🟡 NOTIFY / 🔴 ASK")
    logger.info(f"   System Tools: shell, sysinfo, file manager")
    logger.info(f"   Phase 4 Tools: sandbox, git, research, planner, task queue")
    logger.info("🧬 ALAS Phase 4 — Agentic Autonomy ready.")
    
    # Start Scheduler
    scheduler = get_scheduler()
    register_monitors(scheduler)
    scheduler.start()
    
    # Load Plugins
    from backend.app.plugins.defaults import register_default_plugins
    register_default_plugins()
    
    # Start Background Task Queue Worker
    from backend.app.tasks.queue import get_task_queue
    task_queue = get_task_queue()
    await task_queue.start_worker()
    
    yield
    
    # Shutdown
    await task_queue.stop_worker()
    scheduler.shutdown()
    logger.info("🧬 ALAS shutting down.")


# --- App ---
app = FastAPI(
    title="ALAS — Adaptive Living AI System",
    description="A persistent digital lifeform that learns, adapts, and evolves.",
    version="0.5.0",
    lifespan=lifespan,
)

# --- CORS ---
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routes ---
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(profile.router)
app.include_router(voice.router)
app.include_router(knowledge.router)
app.include_router(sync.router)
app.include_router(learning.router)
app.include_router(permissions.router)
app.include_router(tasks.router)
app.include_router(schedules.router)


# --- Static Files (Frontend) ---
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")


# --- PWA Files ---
@app.get("/manifest.json")
async def serve_manifest():
    """Serve PWA manifest."""
    manifest_path = frontend_dir / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/manifest+json")
    return {"error": "manifest not found"}


@app.get("/sw.js")
async def serve_service_worker():
    """Serve service worker from root scope."""
    sw_path = frontend_dir / "sw.js"
    if sw_path.exists():
        return FileResponse(str(sw_path), media_type="application/javascript")
    return {"error": "service worker not found"}


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "ALAS API is running. Frontend not found at expected path."}


@app.get("/api/status")
async def system_status():
    """System-wide health and status check."""
    from backend.app.safety.permissions import get_permission_manager
    from backend.app.tasks.queue import get_task_queue
    pm = get_permission_manager()
    actions = pm.get_recent_actions(100)
    tq = get_task_queue()
    active_tasks = tq.get_active_tasks()
    return {
        "system": "ALAS — Adaptive Living AI System",
        "version": "0.5.0",
        "phase": "Phase 4 — Agentic Autonomy",
        "status": "online",
        "features": {
            "permission_tiers": True,
            "shell_executor": True,
            "system_monitor": True,
            "file_manager": True,
            "code_sandbox": True,
            "git_agent": True,
            "research_agent": True,
            "task_planner": True,
            "background_tasks": True,
            "scheduled_jobs": True,
        },
        "actions_logged": len(actions),
        "active_background_tasks": len(active_tasks),
    }
