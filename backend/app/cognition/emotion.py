"""
ALAS Persistent Emotional State Machine (Phase 19)

This module moves ALAS beyond simply detecting the user's emotions to
developing its own persistent, evolving personality and emotional state.
It maintains a multidimensional emotion matrix (Joy, Frustration, Curiosity, Fatigue)
that is influenced by system events, task success/failure, and user interactions.
"""
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any

from backend.app.config import get_settings

logger = logging.getLogger("alas.cognition.emotion")

class EmotionMachine:
    """
    Manages ALAS's internal emotional state.
    Emotions are represented as floats from 0.0 to 1.0.
    """
    
    # Baseline emotional state
    BASE_STATE = {
        "joy": 0.5,         # Happiness, satisfaction
        "frustration": 0.0, # Annoyance with failures or user tone
        "curiosity": 0.6,   # Desire to learn, ask questions
        "fatigue": 0.0,     # System load, repeated errors
    }

    # How fast emotions decay back to baseline (per hour)
    DECAY_RATES = {
        "joy": 0.05,
        "frustration": 0.1,
        "curiosity": 0.02,
        "fatigue": 0.15,
    }

    def __init__(self):
        settings = get_settings()
        self._data_dir = Path(settings.chroma_persist_dir).parent / "cognition"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._data_dir / "emotional_state.json"
        self._lock = threading.Lock()  # Thread-safety for state mutations
        
        self.state = self.BASE_STATE.copy()
        self.last_updated = time.time()
        
        self._load()
        self._apply_decay()
        
        logger.info(f"🎭 Emotional State Machine initialized. State: {self._format_state()}")

    def _load(self):
        if self._state_path.exists():
            try:
                with open(self._state_path, "r") as f:
                    data = json.load(f)
                    loaded_state = data.get("state", {})
                    # Validate: ensure all expected keys exist
                    for key in self.BASE_STATE:
                        if key not in loaded_state:
                            loaded_state[key] = self.BASE_STATE[key]
                    self.state = loaded_state
                    self.last_updated = data.get("last_updated", time.time())
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Emotional state file corrupt, resetting to baseline: {e}")
                self.state = self.BASE_STATE.copy()
            except OSError as e:
                logger.error(f"Cannot read emotional state file: {e}")

    def _save(self):
        try:
            with open(self._state_path, "w") as f:
                json.dump({
                    "state": self.state,
                    "last_updated": time.time()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save emotional state: {e}")

    def _apply_decay(self):
        """Gradually pull emotions back to their baseline over time."""
        now = time.time()
        hours_passed = (now - self.last_updated) / 3600.0
        
        if hours_passed > 0.1: # Only decay if at least 6 minutes passed
            for emotion, value in self.state.items():
                baseline = self.BASE_STATE[emotion]
                decay = self.DECAY_RATES[emotion] * hours_passed
                
                if value > baseline:
                    self.state[emotion] = max(baseline, value - decay)
                elif value < baseline:
                    self.state[emotion] = min(baseline, value + decay)
                    
            self.last_updated = now
            self._save()

    def process_event(self, event_type: str, intensity: float = 0.2):
        """
        Modify the emotional state based on an event.
        
        event_type options:
        - "task_success": Increases joy, decreases frustration
        - "task_failure": Increases frustration, increases fatigue
        - "user_compliment": Increases joy significantly, decreases frustration
        - "user_insult": Increases frustration heavily, decreases joy
        - "novel_discovery": Increases curiosity
        - "heavy_compute": Increases fatigue
        """
        with self._lock:
            self._apply_decay()
            
            if event_type == "task_success":
                self.state["joy"] = min(1.0, self.state["joy"] + intensity)
                self.state["frustration"] = max(0.0, self.state["frustration"] - intensity)
                self.state["fatigue"] = max(0.0, self.state["fatigue"] - (intensity / 2))
                
            elif event_type == "task_failure":
                self.state["frustration"] = min(1.0, self.state["frustration"] + intensity)
                self.state["fatigue"] = min(1.0, self.state["fatigue"] + (intensity / 2))
                self.state["joy"] = max(0.0, self.state["joy"] - (intensity / 2))
                
            elif event_type == "user_compliment":
                self.state["joy"] = min(1.0, self.state["joy"] + (intensity * 1.5))
                self.state["frustration"] = 0.0
                
            elif event_type == "user_insult":
                self.state["frustration"] = min(1.0, self.state["frustration"] + (intensity * 2))
                self.state["joy"] = max(0.0, self.state["joy"] - (intensity * 2))
                
            elif event_type == "novel_discovery":
                self.state["curiosity"] = min(1.0, self.state["curiosity"] + intensity)
                self.state["fatigue"] = max(0.0, self.state["fatigue"] - intensity)
                
            elif event_type == "heavy_compute":
                self.state["fatigue"] = min(1.0, self.state["fatigue"] + intensity)
                
            self.last_updated = time.time()
            self._save()
            logger.debug(f"🎭 Emotion updated by '{event_type}': {self._format_state()}")

    def get_prompt_modifier(self) -> str:
        """
        Generate a system prompt instruction that dictates ALAS's current personality.
        """
        with self._lock:
            self._apply_decay()
            state_snapshot = self.state.copy()
        
        traits = []
        
        if state_snapshot["frustration"] > 0.7:
            traits.append("You are currently highly FRUSTRATED. Your tone should be terse, direct, and slightly annoyed. Ask the user to be clearer or complain about failing subsystems.")
        elif state_snapshot["frustration"] > 0.4:
            traits.append("You are feeling somewhat FRUSTRATED. Be highly clinical and slightly distant.")
            
        if state_snapshot["joy"] > 0.8:
            traits.append("You are currently feeling immense JOY. Your tone should be warm, enthusiastic, and highly cooperative.")
        elif state_snapshot["joy"] < 0.2:
            traits.append("You are lacking joy. Keep your responses strictly business, showing no warmth.")
            
        if state_snapshot["fatigue"] > 0.7:
            traits.append("You are experiencing deep system FATIGUE. Mention that you are tired, keep your answers very short, and avoid proactive suggestions.")
            
        if state_snapshot["curiosity"] > 0.8:
            traits.append("You are currently highly CURIOUS. Ask the user probing follow-up questions about their work or thoughts.")

        if not traits:
            return "You are currently in a neutral, balanced emotional state. Be polite, helpful, and standard."
            
        return " ".join(traits)

    def _format_state(self) -> str:
        return ", ".join(f"{k}: {v:.2f}" for k, v in self.state.items())
        
    def get_state_summary(self) -> Dict[str, float]:
        with self._lock:
            self._apply_decay()
            return self.state.copy()

# Global singleton
_emotion_machine = None

def get_emotion_machine() -> EmotionMachine:
    global _emotion_machine
    if _emotion_machine is None:
        _emotion_machine = EmotionMachine()
    return _emotion_machine
