"""
ALAS AR HUD API (Phase 15 — Embodied Spatial Computing)

Comprehensive headless API for wearable spatial computing devices
(e.g., Meta Ray-Bans, Apple Vision Pro, Xreal Air). Provides:

WebSocket Streams:
- Bidirectional telemetry (GPS, IMU, gaze) ↔ HUD overlays
- Internal monologue streaming to AR audio
- Proactive zone-based notifications

REST Endpoints:
- Spatial anchor CRUD
- Geofence management
- Scene analysis
- Location summary & movement analysis
- Spatial memory queries
"""
import asyncio
import time
import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

from backend.app.embodied.spatial import get_spatial_engine
from backend.app.embodied.spatial_memory import get_spatial_memory
from backend.app.embodied.scene_understanding import get_scene_engine

logger = logging.getLogger("alas.api.ar_hud")
router = APIRouter(prefix="/api/ar", tags=["ar_hud"])

# Store connected AR sessions
active_ar_sessions: Dict[str, WebSocket] = {}


# --- Pydantic Models ---

class SpatialAnchorRequest(BaseModel):
    label: str
    latitude: float
    longitude: float
    altitude: float = 0.0
    radius: float = 50.0
    content: str = ""
    anchor_type: str = "note"  # note, memory, alert, navigation

class GeofenceRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float = 200.0
    zone_type: str = "custom"  # home, work, gym, school, custom

class SpatialMemoryRequest(BaseModel):
    content: str
    latitude: float
    longitude: float
    altitude: float = 0.0
    source: str = "ar_hud"
    emotion: str = "neutral"
    importance: float = 0.5

class NearbyQueryRequest(BaseModel):
    latitude: float
    longitude: float
    radius: float = 300.0
    limit: int = 10

class SceneAnalysisRequest(BaseModel):
    device_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


# --- WebSocket Endpoint ---

@router.websocket("/ws/{device_id}")
async def ar_hud_websocket(websocket: WebSocket, device_id: str):
    """
    Establish a high-speed bidirectional connection with an AR wearable.

    Inbound message types (from glasses):
      - telemetry: GPS, IMU, speed data
      - context_request: Gaze target identification
      - scene_frame: Base64-encoded camera frame
      - voice_command: Transcribed voice input
      - heartbeat: Keep-alive ping

    Outbound message types (to glasses):
      - hud_overlay: Text/data overlay for the HUD
      - monologue: Current internal thought
      - zone_alert: Geofence entry/exit notification
      - anchor_alert: Nearby spatial anchor notification
      - pong: Heartbeat response
    """
    await websocket.accept()
    active_ar_sessions[device_id] = websocket
    spatial_engine = get_spatial_engine()
    spatial_memory = get_spatial_memory()
    scene_engine = get_scene_engine()

    logger.info(f"🕶️ AR HUD Connected: {device_id}")

    # Start the monologue push task
    monologue_task = asyncio.create_task(
        _push_monologue_stream(websocket, device_id)
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "telemetry":
                # Full 6-DOF position update
                result = spatial_engine.update_position(
                    device_id=device_id,
                    coordinates=data.get("coordinates"),
                    heading=data.get("heading", 0.0),
                    pitch=data.get("pitch", 0.0),
                    roll=data.get("roll", 0.0),
                    accuracy=data.get("accuracy", 0.0),
                    speed=data.get("speed", 0.0),
                )

                # Send zone alerts
                for event in result.get("zone_events", []):
                    await websocket.send_json({
                        "type": "zone_alert",
                        "event": event["event"],
                        "zone_name": event["zone"]["name"],
                        "zone_type": event["zone"]["zone_type"],
                        "timestamp": event["timestamp"],
                    })

                # Send nearby anchor alerts
                for anchor in result.get("nearby_anchors", [])[:3]:
                    await websocket.send_json({
                        "type": "anchor_alert",
                        "anchor_id": anchor["anchor_id"],
                        "label": anchor["label"],
                        "content": anchor["content"][:100],
                        "anchor_type": anchor["anchor_type"],
                    })

            elif msg_type == "context_request":
                # Gaze target identification — user is looking at something
                gaze_target = data.get("gaze_target", "")
                
                # Use scene understanding for rich context
                gaze_result = scene_engine.analyze_gaze_target(
                    gaze_target=gaze_target,
                    device_id=device_id,
                )

                # Enrich with spatial context
                spatial_context = spatial_engine.get_spatial_context(
                    target_label=gaze_target,
                    device_id=device_id,
                )

                await websocket.send_json({
                    "type": "hud_overlay",
                    "target": gaze_target,
                    "overlay_text": gaze_result.get("overlay_text", ""),
                    "spatial_context": spatial_context,
                    "knowledge": gaze_result.get("knowledge", []),
                    "actions": gaze_result.get("actions", []),
                })

            elif msg_type == "scene_frame":
                # Camera frame from AR glasses for scene analysis
                import base64
                frame_b64 = data.get("frame", "")
                if frame_b64:
                    try:
                        image_data = base64.b64decode(frame_b64)
                        coords = data.get("coordinates", [0.0, 0.0])
                        lat = coords[0] if len(coords) > 0 else 0.0
                        lon = coords[1] if len(coords) > 1 else 0.0

                        scene = await scene_engine.analyze_frame(
                            image_data=image_data,
                            device_id=device_id,
                            latitude=lat,
                            longitude=lon,
                        )

                        await websocket.send_json({
                            "type": "hud_overlay",
                            "scene": scene.to_dict(),
                            "overlay_text": f"🔍 {scene.environment} ({scene.scene_type}) — {scene.lighting} lighting",
                        })
                    except Exception as e:
                        logger.error(f"Scene frame analysis failed: {e}")

            elif msg_type == "voice_command":
                # Transcribed voice command from AR glasses
                command = data.get("text", "")
                if command:
                    # Route through the main chat engine
                    try:
                        from backend.app.api.chat import get_engine
                        engine = get_engine()
                        response = await engine.generate(
                            message=command,
                            session_id=f"ar_{device_id}",
                            mode="casual",
                        )
                        await websocket.send_json({
                            "type": "hud_overlay",
                            "overlay_text": response[:200],
                            "full_response": response,
                            "source": "voice_command",
                        })
                    except Exception as e:
                        logger.error(f"Voice command processing failed: {e}")
                        await websocket.send_json({
                            "type": "hud_overlay",
                            "overlay_text": f"Error: {e}",
                        })

            elif msg_type == "remember_here":
                # Pin a memory to the current location
                content = data.get("content", "")
                coords = data.get("coordinates", [])
                if content and len(coords) >= 2:
                    mem_id = spatial_memory.store(
                        content=content,
                        latitude=coords[0],
                        longitude=coords[1],
                        altitude=coords[2] if len(coords) > 2 else 0.0,
                        source="ar_hud",
                        emotion=data.get("emotion", "neutral"),
                    )
                    await websocket.send_json({
                        "type": "hud_overlay",
                        "overlay_text": f"📌 Memory pinned: {content[:60]}",
                        "memory_id": mem_id,
                    })

            elif msg_type == "heartbeat":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": time.time(),
                    "server_status": "ok",
                })

    except WebSocketDisconnect:
        logger.info(f"🕶️ AR HUD Disconnected: {device_id}")
    except Exception as e:
        logger.error(f"AR HUD WebSocket Error for {device_id}: {e}")
    finally:
        monologue_task.cancel()
        active_ar_sessions.pop(device_id, None)


async def _push_monologue_stream(websocket: WebSocket, device_id: str):
    """
    Background task that periodically pushes the internal monologue
    to the AR HUD as an ambient thought stream.
    """
    try:
        from backend.app.cognition.monologue import get_monologue
        monologue = get_monologue()
        last_thought = ""

        while True:
            await asyncio.sleep(10)  # Push every 10 seconds

            current = monologue.get_latest_thought()
            if current != last_thought and current:
                try:
                    await websocket.send_json({
                        "type": "monologue",
                        "thought": current,
                        "timestamp": time.time(),
                    })
                    last_thought = current
                except Exception:
                    break  # WebSocket closed
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"Monologue stream ended for {device_id}: {e}")


# --- REST Endpoints: Status ---

@router.get("/status")
async def get_ar_status():
    """Get comprehensive AR subsystem status."""
    spatial_engine = get_spatial_engine()
    scene_engine = get_scene_engine()

    return {
        "active_huds": list(active_ar_sessions.keys()),
        "hud_count": len(active_ar_sessions),
        "spatial_tracking": spatial_engine.is_active(),
        "spatial_stats": spatial_engine.get_stats(),
        "scene_engine": scene_engine.get_environmental_summary(),
        "spatial_memory_stats": get_spatial_memory().get_stats(),
    }


# --- REST Endpoints: Spatial Anchors ---

@router.post("/anchors")
async def create_anchor(request: SpatialAnchorRequest):
    """Create a new spatial anchor pinned to a physical location."""
    engine = get_spatial_engine()
    anchor = engine.create_anchor(
        label=request.label,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude=request.altitude,
        radius=request.radius,
        content=request.content,
        anchor_type=request.anchor_type,
    )
    return {"status": "created", "anchor": anchor.to_dict()}


@router.get("/anchors")
async def list_anchors():
    """List all spatial anchors."""
    engine = get_spatial_engine()
    return {"anchors": engine.get_all_anchors(), "count": len(engine.anchors)}


@router.get("/anchors/{anchor_id}")
async def get_anchor(anchor_id: str):
    """Get a specific spatial anchor."""
    engine = get_spatial_engine()
    anchor = engine.get_anchor(anchor_id)
    if not anchor:
        raise HTTPException(status_code=404, detail="Anchor not found")
    return anchor


@router.delete("/anchors/{anchor_id}")
async def delete_anchor(anchor_id: str):
    """Delete a spatial anchor."""
    engine = get_spatial_engine()
    if engine.delete_anchor(anchor_id):
        return {"status": "deleted", "anchor_id": anchor_id}
    raise HTTPException(status_code=404, detail="Anchor not found")


@router.post("/anchors/nearby")
async def find_nearby_anchors(request: NearbyQueryRequest):
    """Find spatial anchors near a location."""
    engine = get_spatial_engine()
    nearby = engine.get_nearby_anchors(
        latitude=request.latitude,
        longitude=request.longitude,
        max_distance=request.radius,
    )
    return {
        "anchors": [a.to_dict() for a in nearby],
        "count": len(nearby),
        "center": {"lat": request.latitude, "lon": request.longitude},
        "radius": request.radius,
    }


# --- REST Endpoints: Geofences ---

@router.post("/geofences")
async def create_geofence(request: GeofenceRequest):
    """Create a new geofence zone."""
    engine = get_spatial_engine()
    zone = engine.create_geofence(
        name=request.name,
        latitude=request.latitude,
        longitude=request.longitude,
        radius=request.radius,
        zone_type=request.zone_type,
    )
    return {"status": "created", "geofence": zone.to_dict()}


@router.get("/geofences")
async def list_geofences():
    """List all geofence zones."""
    engine = get_spatial_engine()
    return {"geofences": engine.get_all_geofences(), "count": len(engine.geofences)}


@router.delete("/geofences/{zone_id}")
async def delete_geofence(zone_id: str):
    """Delete a geofence zone."""
    engine = get_spatial_engine()
    if engine.delete_geofence(zone_id):
        return {"status": "deleted", "zone_id": zone_id}
    raise HTTPException(status_code=404, detail="Geofence not found")


# --- REST Endpoints: Spatial Memory ---

@router.post("/memories")
async def store_spatial_memory(request: SpatialMemoryRequest):
    """Store a new location-tagged memory."""
    memory = get_spatial_memory()
    mem_id = memory.store(
        content=request.content,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude=request.altitude,
        source=request.source,
        emotion=request.emotion,
        importance=request.importance,
    )
    return {"status": "stored", "memory_id": mem_id}


@router.post("/memories/nearby")
async def recall_nearby_memories(request: NearbyQueryRequest):
    """Retrieve memories near a location."""
    memory = get_spatial_memory()
    nearby = memory.recall_nearby(
        latitude=request.latitude,
        longitude=request.longitude,
        radius=request.radius,
        limit=request.limit,
    )
    return {
        "memories": nearby,
        "count": len(nearby),
        "narrative": memory.get_location_narrative(request.latitude, request.longitude, request.radius),
    }


@router.delete("/memories/{memory_id}")
async def delete_spatial_memory(memory_id: str):
    """Delete a spatial memory."""
    memory = get_spatial_memory()
    if memory.delete(memory_id):
        return {"status": "deleted", "memory_id": memory_id}
    raise HTTPException(status_code=404, detail="Memory not found")


# --- REST Endpoints: Location & Movement ---

@router.get("/location/{device_id}")
async def get_device_location(device_id: str):
    """Get the current location and spatial context for a device."""
    engine = get_spatial_engine()
    position = engine.get_device_position(device_id)
    if not position:
        raise HTTPException(status_code=404, detail=f"No position data for device '{device_id}'")

    return {
        "position": position,
        "summary": engine.get_location_summary(device_id),
        "current_zone": engine.get_current_zone(device_id),
        "movement": engine.get_movement_analysis(device_id),
    }


@router.get("/location/{device_id}/summary")
async def get_location_summary(device_id: str):
    """Get a human-readable location summary for a device."""
    engine = get_spatial_engine()
    return {"summary": engine.get_location_summary(device_id)}


@router.get("/devices")
async def list_tracked_devices():
    """List all devices with their current positions."""
    engine = get_spatial_engine()
    return {
        "devices": engine.get_all_device_positions(),
        "count": len(engine.device_positions),
    }


# --- REST Endpoints: Scene Understanding ---

@router.get("/scene")
async def get_current_scene():
    """Get the current environmental awareness state."""
    scene_engine = get_scene_engine()
    return scene_engine.get_environmental_summary()


# --- Utility: Broadcast to all connected HUDs ---

async def broadcast_to_huds(message: dict):
    """Send a message to all connected AR HUDs."""
    disconnected = []
    for device_id, ws in active_ar_sessions.items():
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(device_id)

    for d in disconnected:
        active_ar_sessions.pop(d, None)
