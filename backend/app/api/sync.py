"""
ALAS Cross-Device Sync API — State export/import for multi-device continuity.

Enables session continuity across devices via:
- Device registration with tokens
- State snapshot export (memories, profile, knowledge graph)
- State import for restoring on new devices
- Pull-based sync with last-sync timestamps
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.memory.retrieval import MemoryRetriever
from backend.app.memory.knowledge_graph import KnowledgeGraph

logger = logging.getLogger("alas.api.sync")
router = APIRouter(prefix="/api/sync", tags=["sync"])

# In-memory device registry (persisted via profile in production)
_devices: dict[str, dict] = {}
_retriever: Optional[MemoryRetriever] = None
_kg: Optional[KnowledgeGraph] = None


def _get_retriever() -> MemoryRetriever:
    global _retriever
    if _retriever is None:
        _retriever = MemoryRetriever()
    return _retriever


def _get_kg() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg


# --- Models ---

class DeviceRegistration(BaseModel):
    device_name: str
    device_type: str = "desktop"  # desktop, mobile, tablet, browser
    user_id: str = "default"


class SyncRequest(BaseModel):
    device_token: str
    last_sync: Optional[str] = None  # ISO timestamp


class StateImportRequest(BaseModel):
    device_token: str
    profile_data: Optional[dict] = None
    knowledge_data: Optional[dict] = None


# --- Endpoints ---

@router.post("/register")
async def register_device(request: DeviceRegistration):
    """
    Register a new device for sync.

    Returns a unique device token for authentication.
    """
    device_token = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    _devices[device_token] = {
        "device_name": request.device_name,
        "device_type": request.device_type,
        "user_id": request.user_id,
        "registered_at": now,
        "last_sync": now,
    }

    logger.info(f"Device registered: {request.device_name} ({request.device_type})")

    return {
        "device_token": device_token,
        "device_name": request.device_name,
        "registered_at": now,
    }


@router.get("/devices")
async def list_devices():
    """List all registered devices."""
    return {
        "devices": [
            {
                "token_preview": token[:8] + "...",
                **info,
            }
            for token, info in _devices.items()
        ]
    }


@router.post("/export")
async def export_state(request: SyncRequest):
    """
    Export current state for syncing to another device.

    Returns a snapshot of:
    - User profile
    - Recent memories
    - Knowledge graph
    - Sync metadata
    """
    device = _devices.get(request.device_token)
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device token")

    retriever = _get_retriever()
    kg = _get_kg()
    now = datetime.now(timezone.utc).isoformat()

    # Get user profile
    user_id = device.get("user_id", "default")
    profile = retriever.profile_store.get_profile(user_id)

    # Get recent memories (since last sync if available)
    memories = retriever.episodic.get_recent(n=100)

    # Filter by last_sync timestamp if provided
    if request.last_sync:
        memories = [
            m for m in memories
            if m.get("metadata", {}).get("timestamp", "") > request.last_sync
        ]

    # Get knowledge graph state
    kg_state = {
        "entities": kg.get_all_entities(limit=500),
        "edges": kg.get_all_edges(),
        "stats": kg.get_stats(),
    }

    # Update last sync time
    _devices[request.device_token]["last_sync"] = now

    return {
        "sync_timestamp": now,
        "device": device.get("device_name"),
        "profile": profile,
        "memories": {
            "count": len(memories),
            "items": memories,
        },
        "knowledge_graph": kg_state,
    }


@router.post("/import")
async def import_state(request: StateImportRequest):
    """
    Import state from another device.

    Merges incoming data with existing state.
    """
    device = _devices.get(request.device_token)
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device token")

    retriever = _get_retriever()
    kg = _get_kg()
    user_id = device.get("user_id", "default")
    imported = {"profile": False, "knowledge": False}

    # Import profile data
    if request.profile_data:
        safe_fields = {
            k: v for k, v in request.profile_data.items()
            if k in ("name", "preferred_name", "communication_style",
                     "preferred_mode", "topics_of_interest", "timezone")
            and v is not None
        }
        if safe_fields:
            retriever.profile_store.update_profile(user_id, **safe_fields)
            imported["profile"] = True

    # Import knowledge graph data
    if request.knowledge_data:
        entities = request.knowledge_data.get("entities", [])
        for entity in entities:
            kg.add_entity(
                name=entity.get("label", entity.get("name", "")),
                entity_type=entity.get("type", "concept"),
                source="sync",
            )

        edges = request.knowledge_data.get("edges", [])
        for edge in edges:
            kg.add_relationship(
                source_name=edge.get("source", ""),
                target_name=edge.get("target", ""),
                relation=edge.get("relation", "related_to"),
            )
        imported["knowledge"] = True

    now = datetime.now(timezone.utc).isoformat()
    _devices[request.device_token]["last_sync"] = now

    return {
        "status": "imported",
        "imported": imported,
        "sync_timestamp": now,
    }


@router.get("/status")
async def sync_status():
    """Get sync system status."""
    return {
        "registered_devices": len(_devices),
        "sync_available": True,
    }
