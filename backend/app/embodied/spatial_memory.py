"""
ALAS Spatial Memory Layer (Phase 15)

Extends the ALAS memory system with location-aware capabilities.
Associates episodic memories with GPS coordinates and enables
proximity-based memory retrieval — "remember what happened here."
"""
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from backend.app.config import get_settings
from backend.app.embodied.spatial import haversine_distance

logger = logging.getLogger("alas.embodied.spatial_memory")


class SpatialMemoryEntry:
    """A memory entry with associated spatial coordinates."""

    def __init__(
        self,
        memory_id: str,
        content: str,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        timestamp: float = 0.0,
        source: str = "conversation",
        emotion: str = "neutral",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ):
        self.memory_id = memory_id
        self.content = content
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.timestamp = timestamp or time.time()
        self.source = source
        self.emotion = emotion
        self.importance = importance
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "timestamp": self.timestamp,
            "source": self.source,
            "emotion": self.emotion,
            "importance": self.importance,
            "metadata": self.metadata,
        }

    def distance_from(self, lat: float, lon: float) -> float:
        return haversine_distance(self.latitude, self.longitude, lat, lon)


class SpatialMemory:
    """
    Location-anchored memory system.

    Stores memories with GPS coordinates and supports spatial queries:
    - "What happened near here?"
    - "What do I remember about this place?"
    - "Show me memories from my walk yesterday."
    """

    def __init__(self):
        settings = get_settings()
        self._data_dir = Path(settings.chroma_persist_dir).parent / "spatial"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._memories_path = self._data_dir / "spatial_memories.json"

        self.memories: Dict[str, SpatialMemoryEntry] = {}
        self._load()

        logger.info(f"🗺️ Spatial Memory initialized: {len(self.memories)} location-tagged memories")

    def _load(self):
        """Load spatial memories from disk."""
        if self._memories_path.exists():
            try:
                with open(self._memories_path) as f:
                    data = json.load(f)
                for entry in data:
                    mem = SpatialMemoryEntry(**entry)
                    self.memories[mem.memory_id] = mem
            except Exception as e:
                logger.error(f"Failed to load spatial memories: {e}")

    def _save(self):
        """Persist spatial memories to disk."""
        try:
            with open(self._memories_path, "w") as f:
                json.dump(
                    [m.to_dict() for m in self.memories.values()],
                    f, indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save spatial memories: {e}")

    def store(
        self,
        content: str,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        source: str = "conversation",
        emotion: str = "neutral",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Store a new spatial memory.

        Args:
            content: The memory content (text).
            latitude: GPS latitude.
            longitude: GPS longitude.
            altitude: GPS altitude (optional).
            source: Origin of the memory (conversation, observation, ar_hud).
            emotion: Emotional context when memory was formed.
            importance: Importance score (0.0 to 1.0).
            metadata: Additional metadata dict.

        Returns:
            The generated memory ID.
        """
        import uuid
        memory_id = f"smem_{uuid.uuid4().hex[:10]}"

        entry = SpatialMemoryEntry(
            memory_id=memory_id,
            content=content,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            source=source,
            emotion=emotion,
            importance=importance,
            metadata=metadata,
        )

        self.memories[memory_id] = entry
        self._save()

        logger.info(
            f"🗺️ Spatial memory stored: '{content[:50]}...' at "
            f"({latitude:.5f}, {longitude:.5f})"
        )
        return memory_id

    def recall_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: float = 200.0,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> List[Dict]:
        """
        Retrieve memories near a GPS location.

        Args:
            latitude: Center latitude.
            longitude: Center longitude.
            radius: Search radius in meters.
            limit: Maximum number of results.
            min_importance: Minimum importance threshold.

        Returns:
            List of nearby memories sorted by distance.
        """
        nearby = []

        for mem in self.memories.values():
            if mem.importance < min_importance:
                continue

            dist = mem.distance_from(latitude, longitude)
            if dist <= radius:
                entry = mem.to_dict()
                entry["distance_m"] = round(dist, 1)
                nearby.append(entry)

        # Sort by distance (closest first)
        nearby.sort(key=lambda x: x["distance_m"])
        return nearby[:limit]

    def recall_by_time_range(
        self,
        start_time: float,
        end_time: float,
        limit: int = 50,
    ) -> List[Dict]:
        """Retrieve spatial memories within a time range."""
        results = []
        for mem in self.memories.values():
            if start_time <= mem.timestamp <= end_time:
                results.append(mem.to_dict())

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]

    def recall_by_zone(
        self,
        zone_lat: float,
        zone_lon: float,
        zone_radius: float,
        limit: int = 20,
    ) -> List[Dict]:
        """Retrieve all memories that were formed inside a geofence zone."""
        return self.recall_nearby(zone_lat, zone_lon, radius=zone_radius, limit=limit)

    def get_location_narrative(self, latitude: float, longitude: float, radius: float = 300.0) -> str:
        """
        Generate a human-readable narrative of what ALAS knows about a location.
        Used by the AR HUD to provide contextual overlays.
        """
        nearby = self.recall_nearby(latitude, longitude, radius=radius, limit=10)

        if not nearby:
            return "No memories associated with this location yet."

        lines = [f"🗺️ **{len(nearby)} memories near this location:**\n"]
        for mem in nearby:
            from datetime import datetime
            ts = datetime.fromtimestamp(mem["timestamp"]).strftime("%b %d, %H:%M")
            dist = mem["distance_m"]
            content = mem["content"][:120]
            emotion = mem.get("emotion", "")
            emotion_icon = {
                "joy": "😊", "stress": "😰", "surprise": "😲",
                "neutral": "😐", "": ""
            }.get(emotion, "💭")
            lines.append(f"  {emotion_icon} [{ts}] ({dist:.0f}m) {content}")

        return "\n".join(lines)

    def delete(self, memory_id: str) -> bool:
        """Delete a spatial memory by ID."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get spatial memory statistics."""
        if not self.memories:
            return {"total_memories": 0}

        importances = [m.importance for m in self.memories.values()]
        sources = {}
        for m in self.memories.values():
            sources[m.source] = sources.get(m.source, 0) + 1

        return {
            "total_memories": len(self.memories),
            "avg_importance": round(sum(importances) / len(importances), 2),
            "sources": sources,
        }


# Global singleton
_spatial_memory: Optional[SpatialMemory] = None


def get_spatial_memory() -> SpatialMemory:
    global _spatial_memory
    if _spatial_memory is None:
        _spatial_memory = SpatialMemory()
    return _spatial_memory
