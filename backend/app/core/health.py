"""
ALAS Health Registry — Tracks real subsystem status.

Replaces the old `/api/status` endpoint that always returned True for
every feature. Now each subsystem registers itself and reports real health.
"""

import logging
import time
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("alas.core.health")


class SubsystemStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"      # Partially working
    UNAVAILABLE = "unavailable" # Failed to start
    UNKNOWN = "unknown"


@dataclass
class SubsystemHealth:
    name: str
    status: SubsystemStatus = SubsystemStatus.UNKNOWN
    message: str = ""
    last_checked: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "last_checked": self.last_checked,
            "error": self.error,
        }


class HealthRegistry:
    """
    Central registry for all subsystem health statuses.
    
    Subsystems register themselves at startup and update their status.
    The `/api/health` endpoint queries this registry for real data.
    """

    def __init__(self):
        self._subsystems: Dict[str, SubsystemHealth] = {}

    def register(self, name: str, status: SubsystemStatus = SubsystemStatus.UNKNOWN, message: str = ""):
        """Register a subsystem with its initial status."""
        self._subsystems[name] = SubsystemHealth(
            name=name,
            status=status,
            message=message,
            last_checked=time.time(),
        )

    def update(self, name: str, status: SubsystemStatus, message: str = "", error: Optional[str] = None):
        """Update a subsystem's health status."""
        if name not in self._subsystems:
            self.register(name)
        
        sub = self._subsystems[name]
        sub.status = status
        sub.message = message
        sub.error = error
        sub.last_checked = time.time()

    def mark_healthy(self, name: str, message: str = ""):
        self.update(name, SubsystemStatus.HEALTHY, message)

    def mark_degraded(self, name: str, message: str = "", error: str = ""):
        self.update(name, SubsystemStatus.DEGRADED, message, error)

    def mark_unavailable(self, name: str, error: str = ""):
        self.update(name, SubsystemStatus.UNAVAILABLE, error=error)
        logger.warning(f"⚠️ Subsystem '{name}' marked UNAVAILABLE: {error}")

    def get_status(self, name: str) -> Optional[SubsystemHealth]:
        return self._subsystems.get(name)

    def is_healthy(self, name: str) -> bool:
        sub = self._subsystems.get(name)
        return sub is not None and sub.status == SubsystemStatus.HEALTHY

    def get_full_report(self) -> dict:
        """Get the complete health report for all subsystems."""
        total = len(self._subsystems)
        healthy = sum(1 for s in self._subsystems.values() if s.status == SubsystemStatus.HEALTHY)
        degraded = sum(1 for s in self._subsystems.values() if s.status == SubsystemStatus.DEGRADED)
        unavailable = sum(1 for s in self._subsystems.values() if s.status == SubsystemStatus.UNAVAILABLE)
        
        overall = "healthy"
        if unavailable > 0:
            overall = "degraded"
        if healthy == 0:
            overall = "critical"

        return {
            "overall": overall,
            "summary": f"{healthy}/{total} healthy, {degraded} degraded, {unavailable} unavailable",
            "subsystems": {
                name: sub.to_dict() for name, sub in self._subsystems.items()
            },
        }

    def get_capabilities(self) -> Dict[str, bool]:
        """Returns a dict of feature_name → is_available for frontend adaptation."""
        return {
            name: sub.status in (SubsystemStatus.HEALTHY, SubsystemStatus.DEGRADED)
            for name, sub in self._subsystems.items()
        }


# Global singleton
_health_registry: Optional[HealthRegistry] = None


def get_health_registry() -> HealthRegistry:
    global _health_registry
    if _health_registry is None:
        _health_registry = HealthRegistry()
    return _health_registry
