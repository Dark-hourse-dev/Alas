"""
ALAS Implicit Feedback Tracking.

Monitors conversations to deduce how well the AI is performing without
requiring explicit user ratings. Calculates a 'session fitness score'
used to evolve behaviors.
"""

import logging
import math
from typing import List

logger = logging.getLogger("alas.learning.feedback")

class FeedbackTracker:
    def __init__(self):
        self.session_metrics = {}

    def initialize_session(self, session_id: str):
        if session_id not in self.session_metrics:
            self.session_metrics[session_id] = {
                "message_count": 0,
                "user_words": 0,
                "assistant_words": 0,
                "corrections": 0,
                "positive_sentiment_trend": 0.0,
                "task_completions": 0
            }

    def log_interaction(self, session_id: str, user_text: str, assistant_text: str, emotion: dict = None):
        """Analyze an interaction pair for implicit signals."""
        self.initialize_session(session_id)
        metrics = self.session_metrics[session_id]
        
        metrics["message_count"] += 1
        metrics["user_words"] += len(user_text.split())
        metrics["assistant_words"] += len(assistant_text.split())
        
        # Simple heuristic: if the user sends a very short message like "no", "wrong", "stop"
        # right after a long assistant response, it's likely a correction.
        correction_keywords = ["no", "wrong", "stop", "incorrect", "actually", "wait", "not quite"]
        if any(kw in user_text.lower() for kw in correction_keywords) and len(user_text.split()) < 15:
            metrics["corrections"] += 1
            
        # Track sentiment trend if emotion data is available
        if emotion:
            score = emotion.get("intensity", 0.0)
            label = emotion.get("label", "neutral")
            
            # Very basic sentiment mapping
            val = 0.0
            if label in ["joy", "amusement", "excitement"]:
                val = score
            elif label in ["anger", "frustration", "sadness"]:
                val = -score
                
            metrics["positive_sentiment_trend"] += val

    def calculate_fitness(self, session_id: str) -> float:
        """
        Calculate a fitness score (0.0 to 1.0) for the session.
        Higher is better.
        """
        if session_id not in self.session_metrics:
            return 0.5
            
        metrics = self.session_metrics[session_id]
        
        if metrics["message_count"] == 0:
            return 0.5
            
        # Base fitness starts at 0.7
        fitness = 0.7
        
        # Penalize for corrections (high penalty)
        correction_rate = metrics["corrections"] / metrics["message_count"]
        fitness -= (correction_rate * 1.5)
        
        # Reward for positive sentiment trend
        sentiment_avg = metrics["positive_sentiment_trend"] / metrics["message_count"]
        fitness += (sentiment_avg * 0.2)
        
        # Reward balanced conversation (avoiding monologues if user speaks little)
        # We don't want the AI outputting 1000 words if the user says 2 words.
        if metrics["user_words"] > 0:
            ratio = metrics["assistant_words"] / metrics["user_words"]
            if ratio > 10.0:
                fitness -= 0.1
                
        # Clamp between 0.0 and 1.0
        return max(0.0, min(1.0, fitness))

    def get_metrics(self, session_id: str) -> dict:
        return self.session_metrics.get(session_id, {})

# Singleton instance
_feedback_tracker = None

def get_feedback_tracker() -> FeedbackTracker:
    global _feedback_tracker
    if _feedback_tracker is None:
        _feedback_tracker = FeedbackTracker()
    return _feedback_tracker
