"""
ALAS Sensory Mastery — Real-Time Microphone Sensor (Phase 6)

Continuously analyzes WebRTC audio frames to detect Voice Activity (VAD).
Tracks:
- User Speaking (True/False based on RMS energy)
- Volume Level
"""
import time
import numpy as np
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger("alas.sensors.mic")

class MicSensor:
    def __init__(self, threshold=0.015):
        self._lock = threading.Lock()
        self.threshold = threshold
        
        # Latest tracked state
        self.state = {
            "is_speaking": False,
            "volume": 0.0,
            "last_updated": 0,
            "error": None
        }

    def push_frame(self, audio_data: np.ndarray):
        """
        Process a raw audio array from WebRTC.
        audio_data: numpy array of audio samples
        """
        try:
            # Calculate Root Mean Square (RMS) for volume energy
            if audio_data.dtype != np.float32:
                # normalize to -1.0 to 1.0 if int16
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data
                
            rms = np.sqrt(np.mean(audio_float**2))
            
            is_speaking = bool(rms > self.threshold)
            
            with self._lock:
                self.state = {
                    "is_speaking": is_speaking,
                    "volume": float(rms),
                    "last_updated": time.time(),
                    "error": None
                }
        except Exception as e:
            with self._lock:
                self.state["error"] = str(e)
            logger.error(f"MicSensor error: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get the latest sensor state (thread-safe copy)."""
        with self._lock:
            # Auto-reset if no frames received in the last 0.5 seconds
            if time.time() - self.state["last_updated"] > 0.5:
                self.state["is_speaking"] = False
                self.state["volume"] = 0.0
            return dict(self.state)

# Global singleton
_mic_sensor = MicSensor()

def get_mic_sensor() -> MicSensor:
    return _mic_sensor
