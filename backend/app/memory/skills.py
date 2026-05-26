"""
ALAS Skill Memory (L5).

Stores explicit procedural knowledge and step-by-step guidelines
that the AI has learned for specific complex tasks.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

from backend.app.config import get_settings

logger = logging.getLogger("alas.memory.skills")

class SkillMemory:
    def __init__(self):
        settings = get_settings()
        self.data_dir = Path(settings.chroma_persist_dir).parent / "skills"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "skills.json"
        self.skills = self._load_skills()

    def _load_skills(self) -> Dict[str, dict]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    return json.loads(f.read())
            except Exception as e:
                logger.error(f"Failed to load skills DB: {e}")
        return {}

    def _save_skills(self):
        with open(self.db_path, "w") as f:
            f.write(json.dumps(self.skills, indent=2))

    def add_skill(self, skill_name: str, steps: List[str], description: str):
        """Add a new procedural skill."""
        self.skills[skill_name] = {
            "description": description,
            "steps": steps,
            "usage_count": 0
        }
        self._save_skills()
        logger.info(f"Learned new skill: {skill_name}")

    def get_skill(self, skill_name: str) -> dict:
        """Retrieve a skill and increment its usage counter."""
        if skill_name in self.skills:
            self.skills[skill_name]["usage_count"] += 1
            self._save_skills()
            return self.skills[skill_name]
        return None

    def search_skills(self, query: str) -> List[dict]:
        """Simple keyword search for relevant skills."""
        results = []
        q = query.lower()
        for name, data in self.skills.items():
            if q in name.lower() or q in data["description"].lower():
                results.append({"name": name, **data})
        return results

# Singleton
_skill_memory = None

def get_skill_memory() -> SkillMemory:
    global _skill_memory
    if _skill_memory is None:
        _skill_memory = SkillMemory()
    return _skill_memory
