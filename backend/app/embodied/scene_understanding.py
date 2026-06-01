"""
ALAS Scene Understanding Engine (Phase 15)

Processes visual input from AR wearable cameras to provide spatial context:
- Object/scene recognition via the ALAS vision engine
- Contextual analysis combining visual + spatial data
- Gaze-target identification for AR overlay generation
- Environmental awareness (indoor/outdoor, lighting, crowd density)
"""
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("alas.embodied.scene_understanding")


class SceneContext:
    """Represents the analyzed context of a visual scene."""

    def __init__(
        self,
        scene_type: str = "unknown",
        objects: Optional[List[str]] = None,
        description: str = "",
        environment: str = "unknown",
        lighting: str = "normal",
        crowd_level: str = "none",
        timestamp: float = 0.0,
    ):
        self.scene_type = scene_type  # indoor, outdoor, workspace, transit, etc.
        self.objects = objects or []
        self.description = description
        self.environment = environment  # office, street, park, home, store, etc.
        self.lighting = lighting  # dark, dim, normal, bright
        self.crowd_level = crowd_level  # none, sparse, moderate, crowded
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "scene_type": self.scene_type,
            "objects": self.objects,
            "description": self.description,
            "environment": self.environment,
            "lighting": self.lighting,
            "crowd_level": self.crowd_level,
            "timestamp": self.timestamp,
        }


class SceneUnderstandingEngine:
    """
    Combines AR camera input with spatial data to build a rich
    understanding of the user's physical environment.
    """

    def __init__(self):
        self._last_scene: Optional[SceneContext] = None
        self._scene_history: List[Dict] = []
        self._max_history = 50

    async def analyze_frame(
        self,
        image_data: bytes,
        device_id: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> SceneContext:
        """
        Analyze a camera frame from an AR wearable.

        Uses the ALAS vision engine for scene description and object detection,
        then enriches with spatial context.
        """
        scene = SceneContext()

        # 1. Run vision analysis
        try:
            from backend.app.llm.vision import get_vision_engine
            vision_engine = await get_vision_engine()

            result = await vision_engine.analyze_image(
                image_data=image_data,
                prompt="Describe this scene briefly. List the main objects visible. Is it indoor or outdoor? Describe the lighting and how many people are visible.",
                task="analyze",
            )

            if result.get("status") == "success":
                description = result.get("description", "")
                scene.description = description

                # Extract scene properties from description
                desc_lower = description.lower()

                # Detect indoor/outdoor
                if any(w in desc_lower for w in ["outdoor", "street", "park", "sky", "trees", "road"]):
                    scene.scene_type = "outdoor"
                elif any(w in desc_lower for w in ["indoor", "room", "office", "desk", "wall", "ceiling"]):
                    scene.scene_type = "indoor"

                # Detect environment type
                env_keywords = {
                    "office": ["desk", "computer", "monitor", "office", "keyboard"],
                    "street": ["road", "car", "sidewalk", "traffic", "street"],
                    "park": ["tree", "grass", "bench", "park", "garden"],
                    "home": ["couch", "sofa", "tv", "kitchen", "bed"],
                    "store": ["shelf", "product", "aisle", "store", "shop"],
                    "restaurant": ["table", "food", "menu", "restaurant", "cafe"],
                    "transit": ["bus", "train", "station", "platform", "subway"],
                }
                for env, keywords in env_keywords.items():
                    if any(kw in desc_lower for kw in keywords):
                        scene.environment = env
                        break

                # Detect lighting
                if any(w in desc_lower for w in ["dark", "night", "dim"]):
                    scene.lighting = "dark"
                elif any(w in desc_lower for w in ["bright", "sunny", "sunlight"]):
                    scene.lighting = "bright"
                else:
                    scene.lighting = "normal"

                # Detect crowd
                if any(w in desc_lower for w in ["crowded", "many people", "crowd", "packed"]):
                    scene.crowd_level = "crowded"
                elif any(w in desc_lower for w in ["several people", "some people", "few people"]):
                    scene.crowd_level = "moderate"
                elif any(w in desc_lower for w in ["person", "someone", "one person"]):
                    scene.crowd_level = "sparse"
                else:
                    scene.crowd_level = "none"

        except Exception as e:
            logger.error(f"Vision analysis failed for scene understanding: {e}")
            scene.description = f"Vision analysis unavailable: {e}"

        # 2. Enrich with spatial context
        if latitude != 0.0 or longitude != 0.0:
            try:
                from backend.app.embodied.spatial_memory import get_spatial_memory
                spatial_mem = get_spatial_memory()
                nearby = spatial_mem.recall_nearby(latitude, longitude, radius=100, limit=3)
                if nearby:
                    scene.objects.append(f"[{len(nearby)} nearby memories]")
            except Exception:
                pass

        # Store in history
        self._last_scene = scene
        self._scene_history.append(scene.to_dict())
        if len(self._scene_history) > self._max_history:
            self._scene_history = self._scene_history[-self._max_history:]

        return scene

    def analyze_gaze_target(
        self,
        gaze_target: str,
        device_id: str = "",
    ) -> Dict[str, Any]:
        """
        Analyze a gaze target identified by the AR glasses.

        Combines the label with knowledge graph context and spatial data
        to generate a rich HUD overlay.
        """
        result = {
            "target": gaze_target,
            "overlay_text": "",
            "knowledge": [],
            "actions": [],
        }

        # 1. Query Knowledge Graph
        try:
            from backend.app.memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()

            entity = kg.query_entity(gaze_target)
            if entity:
                result["knowledge"].append({
                    "type": entity.get("type", "concept"),
                    "label": entity.get("label", gaze_target),
                    "relations": entity.get("outgoing_relations", [])[:5],
                    "mentions": entity.get("mention_count", 0),
                })
                result["overlay_text"] = f"{entity['label']}: "
                rels = entity.get("outgoing_relations", [])
                if rels:
                    result["overlay_text"] += ", ".join(
                        f"{r['relation']} {r['target']}" for r in rels[:3]
                    )
            else:
                # Try fuzzy search
                search_results = kg.search(gaze_target, limit=3)
                if search_results:
                    result["overlay_text"] = f"Related: {', '.join(r['label'] for r in search_results)}"
                    result["knowledge"] = search_results
                else:
                    result["overlay_text"] = f"Unknown object: {gaze_target}. Say 'remember this' to learn."
        except Exception as e:
            logger.warning(f"KG lookup failed for gaze target: {e}")
            result["overlay_text"] = f"Object detected: {gaze_target}"

        # 2. Suggest contextual actions
        result["actions"] = [
            {"action": "remember", "label": f"Remember '{gaze_target}'"},
            {"action": "search", "label": f"Search for '{gaze_target}'"},
            {"action": "navigate", "label": f"Navigate to '{gaze_target}'"},
        ]

        return result

    def get_environmental_summary(self) -> Dict[str, Any]:
        """Get a summary of the current environmental awareness state."""
        if not self._last_scene:
            return {"status": "no_data", "message": "No scene analysis has been performed yet."}

        return {
            "status": "ok",
            "current_scene": self._last_scene.to_dict(),
            "history_length": len(self._scene_history),
            "last_updated": self._last_scene.timestamp,
        }


# Global singleton
_scene_engine: Optional[SceneUnderstandingEngine] = None


def get_scene_engine() -> SceneUnderstandingEngine:
    global _scene_engine
    if _scene_engine is None:
        _scene_engine = SceneUnderstandingEngine()
    return _scene_engine
