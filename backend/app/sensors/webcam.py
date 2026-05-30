"""
ALAS Sensory Mastery — Real-Time Webcam Sensor (Phase 6)

Continuously analyzes webcam feed in the background using MediaPipe and OpenCV.
Tracks:
- User Presence
- Attention (looking at screen vs away)
- Basic Emotion approximation (Smile/Joy, Frown/Sadness, Surprise)
"""
import time
import math
import logging
import threading
from typing import Dict, Any

import cv2
import numpy as np

logger = logging.getLogger("alas.sensors.webcam")

class WebcamSensor:
    def __init__(self):
        self.is_running = False
        self._thread = None
        self._lock = threading.Lock()
        
        import queue
        self.frame_queue = queue.Queue(maxsize=1)
        
        # Latest tracked state
        self.state = {
            "user_present": False,
            "attention": "unknown",
            "emotion": "neutral",
            "last_updated": 0,
            "error": None
        }
        
    def _calculate_distance(self, p1, p2, shape):
        """Calculate Euclidean distance between two normalized landmarks."""
        x1, y1 = p1.x * shape[1], p1.y * shape[0]
        x2, y2 = p2.x * shape[1], p2.y * shape[0]
        return math.hypot(x2 - x1, y2 - y1)

    def _analyze_face(self, landmarks, frame_shape) -> Dict[str, Any]:
        """Analyze MediaPipe face landmarks to deduce emotion and attention."""
        # MediaPipe Face Mesh landmark indices
        # Lips: 61 (left corner), 291 (right corner), 0 (upper lip), 17 (lower lip)
        # Eyes (approx): 33 (left eye left corner), 133 (left eye right corner)
        # Eyebrows (approx): 105 (left inner), 334 (right inner)
        
        # Calculate mouth width vs height
        mouth_width = self._calculate_distance(landmarks[61], landmarks[291], frame_shape)
        mouth_height = self._calculate_distance(landmarks[0], landmarks[17], frame_shape)
        
        # Calculate eyebrow distance (for anger/frown approximation)
        eyebrow_dist = self._calculate_distance(landmarks[105], landmarks[334], frame_shape)
        
        # Simple Emotion Heuristics
        emotion = "neutral"
        if mouth_height > 10 and mouth_width < 50:
             emotion = "surprise"
        elif mouth_width > 60 and mouth_height > 5:
             emotion = "joy"
        elif eyebrow_dist < 30:
             emotion = "stress" # or anger
             
        # Attention Heuristic (Nose tip 1, relative to face edges 234, 454)
        nose = landmarks[1]
        left_edge = landmarks[234]
        right_edge = landmarks[454]
        
        nose_to_left = self._calculate_distance(nose, left_edge, frame_shape)
        nose_to_right = self._calculate_distance(nose, right_edge, frame_shape)
        
        attention = "focused"
        if nose_to_left > nose_to_right * 2 or nose_to_right > nose_to_left * 2:
            attention = "distracted" # Looking away sideways
            
        return {
            "emotion": emotion,
            "attention": attention
        }

    def push_frame(self, image):
        """Push a frame from WebRTC to the sensor's processing queue."""
        import queue
        try:
            self.frame_queue.put_nowait(image)
        except queue.Full:
            try:
                self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(image)
            except queue.Empty:
                pass

    def _capture_loop(self):
        """Background thread loop to continuously read and process frames."""
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python import BaseOptions
            import os
            
            model_path = os.path.join(os.getcwd(), 'backend', 'data', 'face_landmarker.task')
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found at {model_path}")
                
            base_options = BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=1
            )
            detector = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            with self._lock:
                self.state["error"] = f"MediaPipe load error: {e}"
            logger.error(f"MediaPipe error: {e}. Webcam sensor disabled.")
            return

        logger.info("🎥 Webcam sensor started (Waiting for WebRTC frames).")
        
        while self.is_running:
            import queue
            try:
                image = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                with self._lock:
                    self.state = {
                        "user_present": False,
                        "attention": "absent",
                        "emotion": "none",
                        "last_updated": time.time(),
                        "error": None
                    }
                continue

            # Convert to RGB and wrap in mp.Image
            image.flags.writeable = False
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            
            results = detector.detect(mp_image)
            
            # Update state
            if results.face_landmarks:
                landmarks = results.face_landmarks[0]
                analysis = self._analyze_face(landmarks, image.shape)
                
                with self._lock:
                    self.state = {
                        "user_present": True,
                        "attention": analysis["attention"],
                        "emotion": analysis["emotion"],
                        "last_updated": time.time(),
                        "error": None
                    }
            else:
                with self._lock:
                    self.state = {
                        "user_present": False,
                        "attention": "absent",
                        "emotion": "none",
                        "last_updated": time.time(),
                        "error": None
                    }
            
            # Sleep to save CPU (process at ~5 FPS)
            time.sleep(0.2)
            
        detector.close()
        logger.info("🎥 Webcam sensor stopped.")

    def start(self):
        """Start the background sensor thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background sensor thread."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_state(self) -> Dict[str, Any]:
        """Get the latest sensor state (thread-safe copy)."""
        with self._lock:
            return dict(self.state)

# Global singleton
_webcam_sensor = WebcamSensor()

def get_webcam_sensor() -> WebcamSensor:
    return _webcam_sensor
