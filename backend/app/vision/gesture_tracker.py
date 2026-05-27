import logging
from typing import List, Dict, Any, Optional
import cv2
import mediapipe as mp

logger = logging.getLogger("alas.vision.gesture")

class GestureTracker:
    """
    ALAS Gesture and Motion Tracker.
    Uses MediaPipe to detect hand landmarks and recognize basic signs/gestures.
    """
    def __init__(self, static_image_mode: bool = False, max_num_hands: int = 2):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        logger.info("👋 GestureTracker initialized.")

    def _classify_basic_gesture(self, hand_landmarks) -> str:
        """
        A simple heuristic-based classifier for basic hand gestures based on landmarks.
        For production, this would use a trained model or mediapipe tasks API.
        """
        # Landmark indices:
        # 4: Thumb tip, 8: Index tip, 12: Middle tip, 16: Ring tip, 20: Pinky tip
        # 3: Thumb IP, 6: Index PIP, 10: Middle PIP, 14: Ring PIP, 18: Pinky PIP
        
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        
        fingers_up = []
        # Check standard fingers (Index, Middle, Ring, Pinky)
        for tip, pip in zip(tips, pips):
            # In image coordinates, y is 0 at top. So tip.y < pip.y means finger is pointing up.
            if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
                fingers_up.append(True)
            else:
                fingers_up.append(False)
                
        # Thumb is trickier due to orientation, we do a basic x-axis check relative to the palm
        thumb_tip_x = hand_landmarks.landmark[4].x
        thumb_mcp_x = hand_landmarks.landmark[2].x
        
        # This is a very simplified check that assumes hand is upright and facing camera
        thumb_up = hand_landmarks.landmark[4].y < hand_landmarks.landmark[3].y
        
        if fingers_up == [True, True, True, True] and thumb_up:
            return "Open Palm (Stop / Hello)"
        elif fingers_up == [False, False, False, False] and not thumb_up:
            return "Closed Fist"
        elif fingers_up == [True, True, False, False]:
            return "Peace Sign"
        elif fingers_up == [False, False, False, False] and thumb_up:
            return "Thumbs Up"
            
        return "Unknown Gesture"

    def process_frame(self, frame) -> Dict[str, Any]:
        """
        Process an OpenCV BGR frame, detect hands, and extract gestures.
        """
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.hands.process(rgb_frame)
        
        detected_gestures = []
        annotated_frame = frame.copy()
        
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Draw the landmarks
                self.mp_draw.draw_landmarks(
                    annotated_frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS
                )
                
                # Classify the gesture
                gesture = self._classify_basic_gesture(hand_landmarks)
                
                # Determine handedness (Left/Right)
                handedness = "Unknown"
                if results.multi_handedness:
                    handedness = results.multi_handedness[idx].classification[0].label
                
                detected_gestures.append({
                    "hand": handedness,
                    "gesture": gesture
                })
                logger.debug(f"Detected {handedness} hand doing: {gesture}")
                
        return {
            "gestures": detected_gestures,
            "annotated_frame": annotated_frame,
            "raw_results": results
        }
        
    def close(self):
        self.hands.close()
