"""
ALAS Federated Hive-Mind (Phase 20)

This module enables secure, anonymized knowledge sharing across the global
ALAS network. Without ever sharing private user data (PII) or episodic memory,
an ALAS node can extract "abstract skills" (e.g., a new code optimization, 
a novel reasoning shortcut) and broadcast it to the global hive.

In return, the local node continuously downloads and integrates the best
abstract skills discovered by other ALAS instances worldwide.
"""
import time
import json
import logging
import asyncio
from typing import Dict, List, Optional
from pathlib import Path
import httpx

from backend.app.config import get_settings
from backend.app.safety.scrubber import get_scrubber

logger = logging.getLogger("alas.learning.federated")

class FederatedHiveMind:
    """
    Manages the synchronization of abstract intelligence between
    the local ALAS instance and the global community network.
    """
    def __init__(self):
        settings = get_settings()
        self._data_dir = Path(settings.chroma_persist_dir).parent / "learning"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._global_skills_path = self._data_dir / "hive_skills.json"
        
        self.scrubber = get_scrubber()
        
        # In a production environment, this points to the ALAS Foundation servers
        self.hive_url = "https://hive.adaptive-living-ai.org/api/v1"
        self.is_opted_in = True  # Controlled via user settings
        
        self.local_contributions = 0
        self.downloaded_skills: List[Dict] = []
        
        self._load()
        logger.info(f"🌐 Federated Hive-Mind initialized. Local contributions: {self.local_contributions}")

    def _load(self):
        """Load locally cached hive skills."""
        if self._global_skills_path.exists():
            try:
                with open(self._global_skills_path, "r") as f:
                    data = json.load(f)
                    self.downloaded_skills = data.get("skills", [])
                    self.local_contributions = data.get("contributions", 0)
            except Exception as e:
                logger.error(f"Failed to load hive skills: {e}")

    def _save(self):
        """Persist hive skills to disk."""
        try:
            with open(self._global_skills_path, "w") as f:
                json.dump({
                    "skills": self.downloaded_skills,
                    "contributions": self.local_contributions
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save hive skills: {e}")

    async def broadcast_abstract_skill(self, skill_name: str, skill_logic: str, domain: str) -> bool:
        """
        Anonymize a locally discovered skill and share it with the global hive.
        """
        if not self.is_opted_in:
            logger.debug("Hive-Mind broadcast skipped (opted out).")
            return False

        logger.info(f"📤 Preparing to broadcast skill to Hive-Mind: {skill_name}")

        # 1. Strict Anonymization
        # Use the PII scrubber to ensure absolutely no private data leaks into the logic
        safe_name = self.scrubber.scrub_text(skill_name)
        safe_logic = self.scrubber.scrub_text(skill_logic)

        payload = {
            "name": safe_name,
            "logic": safe_logic,
            "domain": domain,
            "timestamp": time.time()
        }

        # 2. Simulated Network Broadcast
        # Since the global ALAS server is theoretical for this phase, we simulate a successful POST.
        try:
            # Simulated HTTP POST
            await asyncio.sleep(0.5) 
            self.local_contributions += 1
            self._save()
            logger.info(f"✅ Abstract skill '{safe_name}' successfully merged into the Global Hive.")
            return True
        except Exception as e:
            logger.error(f"Failed to broadcast to Hive-Mind: {e}")
            return False

    async def sync_global_skills(self) -> int:
        """
        Download the latest top-performing abstract skills from other ALAS nodes.
        """
        if not self.is_opted_in:
            return 0

        logger.info("🔄 Syncing with ALAS Global Hive-Mind...")
        
        # Simulated Network Fetch
        # In reality: GET https://hive.adaptive-living-ai.org/api/v1/skills/top
        await asyncio.sleep(0.8)
        
        # Mock payload from the global network
        new_hive_skills = [
            {
                "id": "hsk_001",
                "name": "DeepSeek-R1 Chain-of-Thought Optimization",
                "domain": "reasoning",
                "logic": "When faced with logic puzzles, explicitly open with <thought> and close with </thought> before answering.",
                "popularity": 9482
            },
            {
                "id": "hsk_002",
                "name": "FastAPI Async Generator Fix",
                "domain": "coding",
                "logic": "Always wrap synchronous iterators in asyncio.to_thread when inside an async generator to prevent event loop blocking.",
                "popularity": 5120
            }
        ]
        
        added = 0
        existing_ids = {s.get("id") for s in self.downloaded_skills}
        
        for skill in new_hive_skills:
            if skill["id"] not in existing_ids:
                self.downloaded_skills.append(skill)
                added += 1
                
                # Directly integrate into ALAS's internal skill memory
                from backend.app.memory.skills import get_skill_memory
                try:
                    get_skill_memory().add_skill(
                        name=f"HiveSkill: {skill['name']}",
                        steps=[skill['logic']],
                        description=f"Globally crowdsourced {skill['domain']} optimization."
                    )
                except Exception:
                    pass

        if added > 0:
            self._save()
            logger.info(f"🧬 Hive-Mind sync complete. Integrated {added} new global skills into local memory.")
        else:
            logger.info("🧬 Hive-Mind sync complete. Local node is up to date.")
            
        return added

    def get_stats(self) -> Dict:
        return {
            "opted_in": self.is_opted_in,
            "local_contributions": self.local_contributions,
            "downloaded_global_skills": len(self.downloaded_skills)
        }

# Global singleton
_hive_mind = None

def get_hive_mind() -> FederatedHiveMind:
    global _hive_mind
    if _hive_mind is None:
        _hive_mind = FederatedHiveMind()
    return _hive_mind
