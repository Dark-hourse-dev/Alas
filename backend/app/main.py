"""
ALAS — Main Application Entry Point.

FastAPI server with WebSocket support, CORS, static file serving,
and all API routes mounted.
"""

import logging
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.config import get_settings, ensure_data_dirs, validate_security
from backend.app.api import chat, memory, profile, voice, knowledge, sync, learning, permissions, tasks, schedules, webrtc, ar_hud
from backend.app.proactive.scheduler import get_scheduler
from backend.app.proactive.monitors import register_monitors
from backend.app.core.health import get_health_registry, SubsystemStatus

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
    """Application startup and shutdown lifecycle with graceful degradation."""
    logger.info("🧬 ALAS — Adaptive Living AI System starting up...")
    ensure_data_dirs()
    settings = get_settings()
    validate_security(settings)
    health = get_health_registry()
    
    logger.info(f"   Model: {settings.ollama_model}")
    logger.info(f"   Ollama: {settings.ollama_host}")
    logger.info(f"   Memory: ChromaDB @ {settings.chroma_persist_dir}")
    logger.info(f"   Profile: SQLite @ {settings.sqlite_db_path}")

    # --- Each subsystem starts independently so one failure doesn't crash everything ---

    # 1. Autonomous Immune System (critical — start first)
    try:
        from backend.app.safety.immune import get_immune_system
        immune = get_immune_system()
        immune.activate()
        health.mark_healthy("immune_system", "Activated")
    except Exception as e:
        logger.error(f"❌ Immune System failed to activate: {e}")
        health.mark_unavailable("immune_system", str(e))

    # 2. Proactive Scheduler
    scheduler = None
    try:
        scheduler = get_scheduler()
        register_monitors(scheduler)
        scheduler.start()
        health.mark_healthy("scheduler", "Running")
    except Exception as e:
        logger.error(f"❌ Scheduler failed: {e}")
        health.mark_unavailable("scheduler", str(e))

    # 3. Plugins
    try:
        from backend.app.plugins.defaults import register_default_plugins
        register_default_plugins()
        health.mark_healthy("plugins", "Loaded")
    except Exception as e:
        logger.warning(f"⚠️ Plugin loading failed: {e}")
        health.mark_degraded("plugins", error=str(e))

    # 4. Background Task Queue
    task_queue = None
    try:
        from backend.app.tasks.queue import get_task_queue
        task_queue = get_task_queue()
        await task_queue.start_worker()
        health.mark_healthy("task_queue", "Worker active")
    except Exception as e:
        logger.error(f"❌ Task queue failed: {e}")
        health.mark_unavailable("task_queue", str(e))

    # 5. Webcam Sensor (Phase 6) — often unavailable on headless/servers
    webcam_sensor = None
    try:
        from backend.app.sensors.webcam import get_webcam_sensor
        webcam_sensor = get_webcam_sensor()
        webcam_sensor.start()
        health.mark_healthy("webcam_sensor", "Streaming")
    except Exception as e:
        logger.warning(f"⚠️ Webcam sensor unavailable (non-critical): {e}")
        health.mark_unavailable("webcam_sensor", str(e))

    # 6. Internal Monologue (Phase 10)
    monologue = None
    try:
        from backend.app.cognition.monologue import get_monologue
        monologue = get_monologue()
        monologue.start()
        health.mark_healthy("monologue", "Background thread active")
    except Exception as e:
        logger.warning(f"⚠️ Internal monologue failed: {e}")
        health.mark_unavailable("monologue", str(e))

    # 7. MCP Manager (ALAS 2.0 Phase 1)
    mcp_manager = None
    try:
        from backend.app.mcp.mcp_manager import get_mcp_manager
        mcp_manager = get_mcp_manager()
        logger.info("   ALAS 2.0: Starting Universal Tool Plug (MCP)...")
        
        # Use project data dir instead of hardcoded /tmp
        mcp_db_dir = Path(settings.chroma_persist_dir).parent / "mcp"
        mcp_db_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(mcp_db_dir / "alas_mcp.db")
        
        asyncio.create_task(mcp_manager.connect_stdio_server(
            "sqlite_mcp", sys.executable, ["-m", "mcp_server_sqlite", "--db-path", db_path]
        ))
        
        workspace_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
        asyncio.create_task(mcp_manager.connect_stdio_server(
            "filesystem_mcp", "npx", ["-y", "@modelcontextprotocol/server-filesystem", workspace_dir]
        ))
        asyncio.create_task(mcp_manager.connect_stdio_server(
            "github_mcp", "npx", ["-y", "@modelcontextprotocol/server-github"]
        ))
        health.mark_healthy("mcp_manager", "Connecting servers")
    except Exception as e:
        logger.warning(f"⚠️ MCP Manager failed: {e}")
        health.mark_unavailable("mcp_manager", str(e))

    # 8. Spatial Engine (Phase 15)
    try:
        from backend.app.embodied.spatial import get_spatial_engine
        spatial_engine = get_spatial_engine()
        logger.info(f"   Phase 15: Spatial Engine loaded — {spatial_engine.get_stats()}")
        health.mark_healthy("spatial_engine", str(spatial_engine.get_stats()))
    except Exception as e:
        logger.warning(f"⚠️ Spatial Engine unavailable: {e}")
        health.mark_unavailable("spatial_engine", str(e))

    # 9. Digital Wallet (Phase 18)
    try:
        from backend.app.economics.wallet import get_wallet_manager
        wallet = get_wallet_manager()
        logger.info(f"   Phase 18: Wallet loaded — {wallet.get_balance('USD')} USD")
        health.mark_healthy("wallet", f"{wallet.get_balance('USD'):.2f} USD")
    except Exception as e:
        logger.warning(f"⚠️ Wallet failed: {e}")
        health.mark_unavailable("wallet", str(e))

    # 10. Federated Hive-Mind (Phase 20)
    try:
        from backend.app.learning.federated import get_hive_mind
        hive = get_hive_mind()
        asyncio.create_task(hive.sync_global_skills())
        health.mark_healthy("hive_mind", "Syncing global skills")
    except Exception as e:
        logger.warning(f"⚠️ Hive-Mind failed: {e}")
        health.mark_unavailable("hive_mind", str(e))

    # --- Startup summary ---
    report = health.get_full_report()
    logger.info(f"🧬 ALAS 3.0 startup complete — {report['summary']}")
    if report["overall"] != "healthy":
        logger.warning(f"   ⚠️ System is running in DEGRADED mode. Some features unavailable.")
    
    yield
    
    # --- Graceful Shutdown ---
    logger.info("🧬 ALAS shutting down...")
    if mcp_manager:
        try:
            await mcp_manager.shutdown()
        except Exception as e:
            logger.error(f"MCP shutdown error: {e}")
    if task_queue:
        try:
            await task_queue.stop_worker()
        except Exception as e:
            logger.error(f"Task queue shutdown error: {e}")
    if scheduler:
        try:
            scheduler.shutdown()
        except Exception as e:
            logger.error(f"Scheduler shutdown error: {e}")
    if webcam_sensor:
        try:
            webcam_sensor.stop()
        except Exception as e:
            logger.error(f"Webcam shutdown error: {e}")
    if monologue:
        try:
            monologue.stop()
        except Exception as e:
            logger.error(f"Monologue shutdown error: {e}")
    logger.info("🧬 ALAS shut down complete.")


# --- App ---
app = FastAPI(
    title="ALAS — Adaptive Living AI System",
    description="A persistent digital lifeform that learns, adapts, and evolves.",
    version="2.0.0",
    lifespan=lifespan,
)

# --- CORS ---
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
app.include_router(webrtc.router)
app.include_router(ar_hud.router)

from backend.app.api import fs
app.include_router(fs.router)

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


@app.get("/api/health")
async def system_health():
    """System-wide health and status check using the Health Registry."""
    from backend.app.core.health import get_health_registry
    registry = get_health_registry()
    
    # Still include some core stats
    try:
        from backend.app.safety.permissions import get_permission_manager
        pm = get_permission_manager()
        actions = pm.get_recent_actions(100)
        actions_len = len(actions)
    except Exception:
        actions_len = 0
        
    try:
        from backend.app.tasks.queue import get_task_queue
        tq = get_task_queue()
        active_tasks = len(tq.get_active_tasks())
    except Exception:
        active_tasks = 0

    try:
        from backend.app.economics.wallet import get_wallet_manager
        wallet_balances = get_wallet_manager().balances
    except Exception:
        wallet_balances = {}
        
    try:
        from backend.app.cognition.emotion import get_emotion_machine
        emotion_matrix = get_emotion_machine().get_state_summary()
    except Exception:
        emotion_matrix = {}
        
    try:
        from backend.app.learning.federated import get_hive_mind
        hive_mind_stats = get_hive_mind().get_stats()
    except Exception:
        hive_mind_stats = {}

    report = registry.get_full_report()
    
    return {
        "system": "ALAS — Adaptive Living AI System",
        "version": "3.0.0",
        "phase": "Phase 20 — Fully Autonomous Node",
        "status": report["overall"],
        "health_report": report,
        "wallet_balances": wallet_balances,
        "emotion_matrix": emotion_matrix,
        "hive_mind_stats": hive_mind_stats,
        "actions_logged": actions_len,
        "active_background_tasks": active_tasks,
    }


@app.get("/api/capabilities")
async def system_capabilities():
    """Returns a simplified dict of available features for frontend UI adaptation."""
    from backend.app.core.health import get_health_registry
    registry = get_health_registry()
    
    # Base capabilities that are always true if the server is running
    caps = {
        "permission_tiers": True,
        "shell_executor": True,
        "system_monitor": True,
        "file_manager": True,
        "code_sandbox": True,
        "semantic_router": True,
        "pii_scrubber": True,
    }
    
    # Dynamic capabilities based on subsystem health
    caps.update(registry.get_capabilities())
    
    return caps
