"""
ALAS Spatial Awareness Engine (Phase 15)

Full spatial computing core for the "Digital Ghost" experience. Provides:
- 6-DOF device tracking (lat, lon, alt, heading, pitch, roll)
- Spatial anchor management (pin knowledge to physical locations)
- Geofence zone detection (home, work, gym, etc.)
- Proximity-based memory retrieval from the Knowledge Graph
- Multi-device spatial relationship awareness
- Location change event detection for proactive notifications
"""
import math
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from backend.app.config import get_settings

logger = logging.getLogger("alas.embodied.spatial")

# --- Geolocation Utilities ---

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two GPS points in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (math.sin(d_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing from point 1 to point 2 in degrees."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)

    x = math.sin(d_lambda) * math.cos(phi2)
    y = (math.cos(phi1) * math.sin(phi2) -
         math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda))

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


# --- Data Models ---

class DevicePosition:
    """Full 6-DOF spatial state for a tracked device."""
    def __init__(
        self,
        device_id: str,
        latitude: float = 0.0,
        longitude: float = 0.0,
        altitude: float = 0.0,
        heading: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
        accuracy: float = 0.0,
        speed: float = 0.0,
        timestamp: float = 0.0,
    ):
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.heading = heading
        self.pitch = pitch
        self.roll = roll
        self.accuracy = accuracy
        self.speed = speed
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "heading": self.heading,
            "pitch": self.pitch,
            "roll": self.roll,
            "accuracy": self.accuracy,
            "speed": self.speed,
            "timestamp": self.timestamp,
        }

    def distance_to(self, other: "DevicePosition") -> float:
        return haversine_distance(
            self.latitude, self.longitude,
            other.latitude, other.longitude
        )

    def bearing_to(self, other: "DevicePosition") -> float:
        return compass_bearing(
            self.latitude, self.longitude,
            other.latitude, other.longitude
        )


class SpatialAnchor:
    """A digital note or knowledge entity pinned to a physical location."""
    def __init__(
        self,
        anchor_id: str,
        label: str,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        radius: float = 50.0,
        content: str = "",
        anchor_type: str = "note",
        created_by: str = "user",
        created_at: str = "",
        metadata: Optional[dict] = None,
    ):
        self.anchor_id = anchor_id
        self.label = label
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.radius = radius  # Activation radius in meters
        self.content = content
        self.anchor_type = anchor_type  # note, memory, alert, navigation
        self.created_by = created_by
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "anchor_id": self.anchor_id,
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "radius": self.radius,
            "content": self.content,
            "anchor_type": self.anchor_type,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    def distance_from(self, lat: float, lon: float) -> float:
        return haversine_distance(self.latitude, self.longitude, lat, lon)

    def is_in_range(self, lat: float, lon: float) -> bool:
        return self.distance_from(lat, lon) <= self.radius


class Geofence:
    """A named geographic zone with defined boundaries."""
    def __init__(
        self,
        zone_id: str,
        name: str,
        latitude: float,
        longitude: float,
        radius: float = 200.0,
        zone_type: str = "custom",
    ):
        self.zone_id = zone_id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.radius = radius
        self.zone_type = zone_type  # home, work, gym, school, custom

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius": self.radius,
            "zone_type": self.zone_type,
        }

    def contains(self, lat: float, lon: float) -> bool:
        dist = haversine_distance(self.latitude, self.longitude, lat, lon)
        return dist <= self.radius


# --- Main Spatial Engine ---

class SpatialEngine:
    """
    Core spatial intelligence system for ALAS Phase 15.

    Manages device positions, spatial anchors, geofences, and provides
    location-aware context retrieval for the AR HUD and agentic tools.
    """

    def __init__(self):
        settings = get_settings()
        self._data_dir = Path(settings.chroma_persist_dir).parent / "spatial"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Runtime state
        self.device_positions: Dict[str, DevicePosition] = {}
        self.anchors: Dict[str, SpatialAnchor] = {}
        self.geofences: Dict[str, Geofence] = {}
        self.active = True

        # Tracking state
        self._last_zone: Dict[str, Optional[str]] = {}  # device_id -> current zone
        self._location_history: Dict[str, List[Dict]] = {}  # device_id -> breadcrumbs
        self._event_callbacks: List = []

        # Load persisted data
        self._load()

        logger.info(
            f"🌐 Spatial Engine initialized: "
            f"{len(self.anchors)} anchors, {len(self.geofences)} geofences"
        )

    # --- Persistence ---

    def _load(self):
        """Load spatial anchors and geofences from disk."""
        anchors_path = self._data_dir / "anchors.json"
        geofences_path = self._data_dir / "geofences.json"

        if anchors_path.exists():
            try:
                with open(anchors_path) as f:
                    data = json.load(f)
                for a in data:
                    self.anchors[a["anchor_id"]] = SpatialAnchor(**a)
            except Exception as e:
                logger.error(f"Failed to load spatial anchors: {e}")

        if geofences_path.exists():
            try:
                with open(geofences_path) as f:
                    data = json.load(f)
                for g in data:
                    self.geofences[g["zone_id"]] = Geofence(**g)
            except Exception as e:
                logger.error(f"Failed to load geofences: {e}")

    def _save(self):
        """Persist spatial anchors and geofences to disk."""
        try:
            with open(self._data_dir / "anchors.json", "w") as f:
                json.dump([a.to_dict() for a in self.anchors.values()], f, indent=2)
            with open(self._data_dir / "geofences.json", "w") as f:
                json.dump([g.to_dict() for g in self.geofences.values()], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save spatial data: {e}")

    # --- Device Tracking ---

    def update_position(
        self,
        device_id: str,
        coordinates: Optional[list] = None,
        heading: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
        accuracy: float = 0.0,
        speed: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Update the 6-DOF position of a tracked device.

        Args:
            device_id: Unique device identifier.
            coordinates: [latitude, longitude] or [lat, lon, altitude].
            heading: Compass heading in degrees (0-360).
            pitch: Device pitch in degrees (-90 to 90).
            roll: Device roll in degrees (-180 to 180).
            accuracy: GPS accuracy in meters.
            speed: Movement speed in m/s.

        Returns:
            Dict with zone changes and nearby anchor triggers.
        """
        if not coordinates or len(coordinates) < 2:
            return {"status": "error", "message": "Coordinates must have at least [lat, lon]"}

        lat, lon = coordinates[0], coordinates[1]
        alt = coordinates[2] if len(coordinates) > 2 else 0.0

        position = DevicePosition(
            device_id=device_id,
            latitude=lat,
            longitude=lon,
            altitude=alt,
            heading=heading,
            pitch=pitch,
            roll=roll,
            accuracy=accuracy,
            speed=speed,
        )
        self.device_positions[device_id] = position

        # Record breadcrumb
        if device_id not in self._location_history:
            self._location_history[device_id] = []
        self._location_history[device_id].append({
            "lat": lat, "lon": lon, "alt": alt,
            "timestamp": time.time(),
        })
        # Keep last 500 breadcrumbs per device
        if len(self._location_history[device_id]) > 500:
            self._location_history[device_id] = self._location_history[device_id][-500:]

        # Detect zone changes
        events = self._detect_zone_events(device_id, lat, lon)

        # Find nearby anchors
        nearby_anchors = self.get_nearby_anchors(lat, lon)

        return {
            "status": "ok",
            "zone_events": events,
            "nearby_anchors": [a.to_dict() for a in nearby_anchors],
        }

    def _detect_zone_events(self, device_id: str, lat: float, lon: float) -> List[Dict]:
        """Detect geofence entry/exit events."""
        events = []
        current_zone = None

        for zone in self.geofences.values():
            if zone.contains(lat, lon):
                current_zone = zone.zone_id
                break

        prev_zone = self._last_zone.get(device_id)

        if current_zone != prev_zone:
            if prev_zone and prev_zone in self.geofences:
                events.append({
                    "event": "zone_exit",
                    "zone": self.geofences[prev_zone].to_dict(),
                    "timestamp": time.time(),
                })
                logger.info(f"📍 Device {device_id} exited zone: {self.geofences[prev_zone].name}")

            if current_zone and current_zone in self.geofences:
                events.append({
                    "event": "zone_enter",
                    "zone": self.geofences[current_zone].to_dict(),
                    "timestamp": time.time(),
                })
                logger.info(f"📍 Device {device_id} entered zone: {self.geofences[current_zone].name}")

        self._last_zone[device_id] = current_zone
        return events

    def get_device_position(self, device_id: str) -> Optional[Dict]:
        """Get the latest known position of a device."""
        pos = self.device_positions.get(device_id)
        return pos.to_dict() if pos else None

    def get_all_device_positions(self) -> List[Dict]:
        """Get positions of all tracked devices."""
        return [p.to_dict() for p in self.device_positions.values()]

    def get_device_proximity(self, device_a: str, device_b: str) -> Optional[Dict]:
        """Calculate distance and bearing between two devices."""
        pos_a = self.device_positions.get(device_a)
        pos_b = self.device_positions.get(device_b)
        if not pos_a or not pos_b:
            return None

        distance = pos_a.distance_to(pos_b)
        bearing = pos_a.bearing_to(pos_b)
        return {
            "distance_meters": round(distance, 2),
            "bearing_degrees": round(bearing, 1),
            "device_a": device_a,
            "device_b": device_b,
        }

    # --- Spatial Anchors ---

    def create_anchor(
        self,
        label: str,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        radius: float = 50.0,
        content: str = "",
        anchor_type: str = "note",
        created_by: str = "user",
        metadata: Optional[dict] = None,
    ) -> SpatialAnchor:
        """Create and persist a new spatial anchor."""
        import uuid
        anchor_id = f"anchor_{uuid.uuid4().hex[:8]}"

        anchor = SpatialAnchor(
            anchor_id=anchor_id,
            label=label,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            radius=radius,
            content=content,
            anchor_type=anchor_type,
            created_by=created_by,
            metadata=metadata,
        )
        self.anchors[anchor_id] = anchor
        self._save()

        # Also index in the Knowledge Graph for semantic retrieval
        try:
            from backend.app.memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            kg.add_entity(
                name=label,
                entity_type="place",
                properties={
                    "latitude": latitude,
                    "longitude": longitude,
                    "content": content,
                    "anchor_id": anchor_id,
                },
                source="spatial_anchor",
            )
        except Exception as e:
            logger.warning(f"Could not index spatial anchor in KG: {e}")

        logger.info(f"📌 Spatial anchor created: '{label}' at ({latitude:.5f}, {longitude:.5f})")
        return anchor

    def delete_anchor(self, anchor_id: str) -> bool:
        """Remove a spatial anchor."""
        if anchor_id in self.anchors:
            del self.anchors[anchor_id]
            self._save()
            return True
        return False

    def get_anchor(self, anchor_id: str) -> Optional[Dict]:
        """Get a single anchor by ID."""
        anchor = self.anchors.get(anchor_id)
        return anchor.to_dict() if anchor else None

    def get_all_anchors(self) -> List[Dict]:
        """Get all spatial anchors."""
        return [a.to_dict() for a in self.anchors.values()]

    def get_nearby_anchors(
        self,
        latitude: float,
        longitude: float,
        max_distance: float = 500.0,
    ) -> List[SpatialAnchor]:
        """Find all anchors within max_distance meters of a point."""
        nearby = []
        for anchor in self.anchors.values():
            dist = anchor.distance_from(latitude, longitude)
            if dist <= max_distance:
                nearby.append(anchor)

        # Sort by distance (closest first)
        nearby.sort(key=lambda a: a.distance_from(latitude, longitude))
        return nearby

    # --- Geofences ---

    def create_geofence(
        self,
        name: str,
        latitude: float,
        longitude: float,
        radius: float = 200.0,
        zone_type: str = "custom",
    ) -> Geofence:
        """Create and persist a new geofence zone."""
        import uuid
        zone_id = f"zone_{uuid.uuid4().hex[:8]}"

        zone = Geofence(
            zone_id=zone_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            zone_type=zone_type,
        )
        self.geofences[zone_id] = zone
        self._save()

        logger.info(f"🔲 Geofence created: '{name}' ({zone_type}) r={radius}m at ({latitude:.5f}, {longitude:.5f})")
        return zone

    def delete_geofence(self, zone_id: str) -> bool:
        """Remove a geofence zone."""
        if zone_id in self.geofences:
            del self.geofences[zone_id]
            self._save()
            return True
        return False

    def get_all_geofences(self) -> List[Dict]:
        """Get all geofence zones."""
        return [g.to_dict() for g in self.geofences.values()]

    def get_current_zone(self, device_id: str) -> Optional[Dict]:
        """Get the zone a device is currently in."""
        pos = self.device_positions.get(device_id)
        if not pos:
            return None

        for zone in self.geofences.values():
            if zone.contains(pos.latitude, pos.longitude):
                return zone.to_dict()
        return None

    # --- Spatial Context ---

    def get_spatial_context(self, target_label: str, device_id: Optional[str] = None) -> str:
        """
        Retrieve rich spatial context for a gaze target or location query.

        Combines:
        1. Knowledge Graph context for the target
        2. Nearby spatial anchors
        3. Current geofence zone
        4. Proximity to other devices
        """
        parts = []

        # 1. Knowledge Graph lookup
        try:
            from backend.app.memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            entity = kg.query_entity(target_label)
            if entity:
                parts.append(f"📖 Known Entity: {entity.get('label', target_label)} ({entity.get('type', 'unknown')})")
                for rel in entity.get("outgoing_relations", [])[:5]:
                    parts.append(f"   → {rel['relation']} → {rel['target']}")
            else:
                related = kg.search(target_label, limit=3)
                if related:
                    parts.append(f"📖 Related entities: {', '.join(r['label'] for r in related)}")
        except Exception as e:
            logger.warning(f"KG lookup failed for spatial context: {e}")

        # 2. Nearby anchors (if we know the device position)
        if device_id and device_id in self.device_positions:
            pos = self.device_positions[device_id]
            nearby = self.get_nearby_anchors(pos.latitude, pos.longitude, max_distance=200)
            if nearby:
                parts.append(f"\n📌 Nearby Anchors ({len(nearby)}):")
                for anchor in nearby[:5]:
                    dist = anchor.distance_from(pos.latitude, pos.longitude)
                    parts.append(f"   • {anchor.label}: {anchor.content[:80]} ({dist:.0f}m away)")

            # 3. Current zone
            zone = self.get_current_zone(device_id)
            if zone:
                parts.append(f"\n📍 Current Zone: {zone['name']} ({zone['zone_type']})")

            # 4. Other devices
            for other_id, other_pos in self.device_positions.items():
                if other_id != device_id:
                    dist = pos.distance_to(other_pos)
                    bearing = pos.bearing_to(other_pos)
                    parts.append(f"\n📱 Device '{other_id}' is {dist:.0f}m away at {bearing:.0f}°")

        if not parts:
            parts.append(f"No spatial context available for '{target_label}'. Creating a new observation point.")

        return "\n".join(parts)

    def get_location_summary(self, device_id: str) -> str:
        """Generate a human-readable summary of the device's current spatial state."""
        pos = self.device_positions.get(device_id)
        if not pos:
            return f"No location data available for device '{device_id}'."

        lines = [
            f"📍 **Location**: ({pos.latitude:.6f}, {pos.longitude:.6f})",
            f"🧭 **Heading**: {pos.heading:.1f}° | **Altitude**: {pos.altitude:.1f}m",
            f"📏 **Accuracy**: ±{pos.accuracy:.1f}m | **Speed**: {pos.speed:.1f} m/s",
        ]

        # Current zone
        zone = self.get_current_zone(device_id)
        if zone:
            lines.append(f"🔲 **Zone**: {zone['name']} ({zone['zone_type']})")
        else:
            lines.append("🔲 **Zone**: Outside all defined zones")

        # Nearby anchors
        nearby = self.get_nearby_anchors(pos.latitude, pos.longitude, max_distance=300)
        if nearby:
            lines.append(f"📌 **Nearby Anchors**: {len(nearby)}")
            for a in nearby[:3]:
                dist = a.distance_from(pos.latitude, pos.longitude)
                lines.append(f"   • {a.label} ({dist:.0f}m)")

        # Breadcrumb trail length
        trail = self._location_history.get(device_id, [])
        if trail:
            duration = time.time() - trail[0].get("timestamp", time.time())
            lines.append(f"🗺️ **Trail**: {len(trail)} points over {duration / 60:.0f} min")

        return "\n".join(lines)

    def get_movement_analysis(self, device_id: str) -> Dict[str, Any]:
        """Analyze the movement pattern of a device from its breadcrumb trail."""
        trail = self._location_history.get(device_id, [])
        if len(trail) < 2:
            return {"status": "insufficient_data", "points": len(trail)}

        total_distance = 0.0
        max_speed = 0.0
        for i in range(1, len(trail)):
            p1, p2 = trail[i - 1], trail[i]
            dist = haversine_distance(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
            dt = p2["timestamp"] - p1["timestamp"]
            speed = dist / dt if dt > 0 else 0
            total_distance += dist
            max_speed = max(max_speed, speed)

        total_time = trail[-1]["timestamp"] - trail[0]["timestamp"]
        avg_speed = total_distance / total_time if total_time > 0 else 0

        # Determine activity
        if avg_speed < 0.5:
            activity = "stationary"
        elif avg_speed < 2.0:
            activity = "walking"
        elif avg_speed < 8.0:
            activity = "running"
        elif avg_speed < 30.0:
            activity = "driving"
        else:
            activity = "high_speed_transit"

        return {
            "status": "ok",
            "total_distance_m": round(total_distance, 1),
            "total_time_s": round(total_time, 1),
            "avg_speed_ms": round(avg_speed, 2),
            "max_speed_ms": round(max_speed, 2),
            "activity": activity,
            "breadcrumb_count": len(trail),
        }

    def is_active(self) -> bool:
        return self.active

    def get_stats(self) -> Dict[str, Any]:
        """Get spatial engine statistics."""
        return {
            "active": self.active,
            "tracked_devices": len(self.device_positions),
            "spatial_anchors": len(self.anchors),
            "geofences": len(self.geofences),
            "total_breadcrumbs": sum(len(v) for v in self._location_history.values()),
        }


# Global Singleton
_spatial_engine: Optional[SpatialEngine] = None


def get_spatial_engine() -> SpatialEngine:
    global _spatial_engine
    if _spatial_engine is None:
        _spatial_engine = SpatialEngine()
    return _spatial_engine
