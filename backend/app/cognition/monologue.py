"""
ALAS Meta-Intelligence — Internal Monologue (Phase 10.4)

Allows ALAS to maintain a continuous background stream of thought,
pondering recent events, sensory data, and user interactions.
"""
import time
import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger("alas.cognition.monologue")

class InternalMonologue:
    def __init__(self):
        self.is_running = False
        self._thread = None
        self._lock = threading.Lock()
        self.current_thought = "I am currently idle."
        self.thought_history = []
        
    def _monologue_loop(self):
        """Background thread loop that periodically generates thoughts."""
        import asyncio
        from backend.app.llm.ollama_client import generate_completion
        from backend.app.sensors.webcam import get_webcam_sensor
        
        logger.info("🧠 Internal Monologue stream started.")
        
        while self.is_running:
            # Gather context
            sensor_state = get_webcam_sensor().get_state()
            
            prompt = (
                f"You are the inner monologue of ALAS. Do not speak to the user. "
                f"Just produce a single, brief internal thought (1-2 sentences) about your current state.\n"
                f"Sensory state: {sensor_state}\n"
                f"Previous thought: {self.current_thought}\n"
                f"What are you pondering right now?"
            )
            
            try:
                # Use a very lightweight model for constant background thinking if possible
                thought = generate_completion(
                    prompt=prompt,
                    system_prompt="You are a silent internal monologue. Think reflectively and analytically.",
                    model="phi3"  # Use lightweight fallback model for background task to save resources
                )
                
                with self._lock:
                    self.current_thought = thought.strip()
                    self.thought_history.append({"time": time.time(), "thought": self.current_thought})
                    
                    if len(self.thought_history) > 100:
                        self.thought_history.pop(0)
                    
                logger.debug(f"🤔 Thought: {self.current_thought}")
                
            except Exception as e:
                logger.error(f"Monologue generation failed: {e}")
                
            # Think every 15 seconds
            time.sleep(15)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._monologue_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_latest_thought(self) -> str:
        with self._lock:
            return self.current_thought

# Global Singleton
_monologue = InternalMonologue()

def get_monologue() -> InternalMonologue:
    return _monologue
