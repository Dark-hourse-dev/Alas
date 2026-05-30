"""
ALAS AR HUD API (Phase 15)

Headless API endpoints designed for wearable spatial computing devices 
(e.g., Meta Ray-Bans, Apple Vision Pro). Exposes internal monologue streams 
and spatial awareness coordinates.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict

from backend.app.embodied.spatial import get_spatial_engine

logger = logging.getLogger("alas.api.ar_hud")
router = APIRouter(prefix="/api/ar", tags=["ar_hud"])

# Store connected AR sessions
active_ar_sessions: Dict[str, WebSocket] = {}

@router.websocket("/ws/{device_id}")
async def ar_hud_websocket(websocket: WebSocket, device_id: str):
    """
    Establish a high-speed websocket connection with an AR wearable.
    Streams internal monologue audio cues and accepts spatial coordinates.
    """
    await websocket.accept()
    active_ar_sessions[device_id] = websocket
    spatial_engine = get_spatial_engine()
    
    logger.info(f"🕶️ AR HUD Connected: {device_id}")
    
    try:
        while True:
            # Wearables stream their IMU and GPS telemetry 
            data = await websocket.receive_json()
            
            if data.get("type") == "telemetry":
                coords = data.get("coordinates")
                heading = data.get("heading")
                
                # Update the system's spatial awareness
                spatial_engine.update_position(device_id, coords, heading)
                
            elif data.get("type") == "context_request":
                # E.g., user is looking at a building, fetch knowledge graph context
                gaze_target = data.get("gaze_target")
                context = spatial_engine.get_spatial_context(gaze_target)
                
                await websocket.send_json({
                    "type": "hud_overlay",
                    "text": f"Object Detected: {gaze_target}",
                    "context": context
                })

    except WebSocketDisconnect:
        logger.info(f"🕶️ AR HUD Disconnected: {device_id}")
        active_ar_sessions.pop(device_id, None)
    except Exception as e:
        logger.error(f"AR HUD WebSocket Error: {e}")
        active_ar_sessions.pop(device_id, None)

@router.get("/status")
async def get_ar_status():
    return {
        "active_huds": list(active_ar_sessions.keys()),
        "spatial_tracking": get_spatial_engine().is_active()
    }
