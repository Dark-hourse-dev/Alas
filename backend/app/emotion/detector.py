"""
ALAS Emotion Detector — Text-based emotional state analysis.

Detects user emotional state from text using keyword patterns
and sentiment heuristics. Feeds into mode adaptation and
memory metadata for behavioral analysis.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("alas.emotion")


# Emotion keyword patterns with associated emotion and intensity
EMOTION_PATTERNS = {
    "joy": {
        "keywords": [
            r"\b(happy|excited|great|awesome|amazing|love|wonderful|fantastic|thrilled|delighted)\b",
            r"\b(yay|woohoo|hurray|haha|lol|😊|😄|🎉|❤️)\b",
            r"\b(thank|grateful|appreciate|blessed)\b",
        ],
        "intensity_boost": 0.1,
    },
    "sadness": {
        "keywords": [
            r"\b(sad|unhappy|depressed|miserable|heartbroken|lonely|disappointed)\b",
            r"\b(crying|tears|miss|lost|grief|mourn)\b",
            r"\b(😢|😭|💔|😞)\b",
        ],
        "intensity_boost": 0.15,
    },
    "anger": {
        "keywords": [
            r"\b(angry|furious|annoyed|irritated|frustrated|mad|pissed|rage)\b",
            r"\b(hate|terrible|awful|worst|stupid|ridiculous)\b",
            r"\b(😡|🤬|😤)\b",
        ],
        "intensity_boost": 0.2,
    },
    "fear": {
        "keywords": [
            r"\b(scared|afraid|anxious|worried|nervous|terrified|panic|dread)\b",
            r"\b(fear|danger|threat|risk|unsafe)\b",
            r"\b(😰|😨|😱)\b",
        ],
        "intensity_boost": 0.15,
    },
    "stress": {
        "keywords": [
            r"\b(stressed|overwhelmed|exhausted|burned.?out|tired|overloaded)\b",
            r"\b(deadline|pressure|too much|can't cope|struggling)\b",
            r"\b(😩|😫|🥵)\b",
        ],
        "intensity_boost": 0.15,
    },
    "curiosity": {
        "keywords": [
            r"\b(curious|wondering|interested|fascinated|intrigued)\b",
            r"\b(how does|what if|why does|tell me|explain)\b",
            r"\b(🤔|💡|🧐)\b",
        ],
        "intensity_boost": 0.05,
    },
    "confusion": {
        "keywords": [
            r"\b(confused|don't understand|makes no sense|unclear|lost)\b",
            r"\b(what\?|huh|wait what|i don't get)\b",
            r"\b(😕|🤷|❓)\b",
        ],
        "intensity_boost": 0.1,
    },
}

# Intensity modifiers
INTENSIFIERS = re.compile(r"\b(very|extremely|really|so|incredibly|absolutely|totally|completely)\b", re.IGNORECASE)
DIMINISHERS = re.compile(r"\b(slightly|somewhat|a bit|kind of|sort of|a little)\b", re.IGNORECASE)

# Negation patterns (reverse emotion)
NEGATION = re.compile(r"\b(not|don't|doesn't|isn't|wasn't|never|no longer|hardly)\b", re.IGNORECASE)


class EmotionDetector:
    """
    Text-based emotion detection using keyword patterns and heuristics.

    Detects primary emotion, intensity (0-1), and suggests appropriate
    interaction mode adjustments.
    """

    # Emotion → recommended mode mapping
    EMOTION_MODE_MAP = {
        "joy": "casual",
        "sadness": "calm",
        "anger": "calm",
        "fear": "calm",
        "stress": "calm",
        "curiosity": "learning",
        "confusion": "learning",
        "neutral": None,  # No mode change
    }

    def detect(self, text: str) -> dict:
        """
        Detect emotional state from text.

        Args:
            text: User's message text.

        Returns:
            Dictionary with:
              - emotion: Primary detected emotion
              - intensity: 0.0 to 1.0
              - all_emotions: Dict of all detected emotions with scores
              - suggested_mode: Recommended mode based on emotion
              - needs_attention: Whether emotion requires special handling
        """
        text_lower = text.lower()
        scores = {}

        # Score each emotion
        for emotion, config in EMOTION_PATTERNS.items():
            score = 0.0
            for pattern in config["keywords"]:
                matches = re.findall(pattern, text_lower)
                score += len(matches) * (0.3 + config["intensity_boost"])
            scores[emotion] = min(score, 1.0)

        # Apply intensity modifiers
        intensifier_count = len(INTENSIFIERS.findall(text))
        diminisher_count = len(DIMINISHERS.findall(text))

        modifier = 1.0 + (intensifier_count * 0.15) - (diminisher_count * 0.1)
        scores = {k: min(v * modifier, 1.0) for k, v in scores.items()}

        # Check for negation (simple approach)
        if NEGATION.search(text_lower):
            # Negation can flip positive emotions
            if scores.get("joy", 0) > 0:
                scores["joy"] *= 0.3

        # Determine primary emotion
        if any(v > 0 for v in scores.values()):
            primary = max(scores, key=scores.get)
            intensity = scores[primary]
        else:
            primary = "neutral"
            intensity = 0.0

        # Determine if attention is needed (high-intensity negative emotions)
        needs_attention = (
            primary in ("sadness", "anger", "fear", "stress")
            and intensity >= 0.5
        )

        suggested_mode = self.EMOTION_MODE_MAP.get(primary)

        return {
            "emotion": primary,
            "intensity": round(intensity, 3),
            "all_emotions": {k: round(v, 3) for k, v in scores.items() if v > 0},
            "suggested_mode": suggested_mode,
            "needs_attention": needs_attention,
        }

    def get_emotional_trend(self, emotion_history: list[dict]) -> dict:
        """
        Analyze emotional trends from a history of detections.

        Args:
            emotion_history: List of past detection results.

        Returns:
            Trend analysis dictionary.
        """
        if not emotion_history:
            return {"trend": "neutral", "stability": 1.0}

        emotions = [h.get("emotion", "neutral") for h in emotion_history]
        intensities = [h.get("intensity", 0) for h in emotion_history]

        # Most frequent emotion
        from collections import Counter
        most_common = Counter(emotions).most_common(1)[0]

        # Stability = how consistent the emotions are (1 = very stable)
        unique_ratio = len(set(emotions)) / len(emotions)
        stability = 1.0 - unique_ratio

        # Average intensity
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0

        return {
            "dominant_emotion": most_common[0],
            "dominant_frequency": most_common[1] / len(emotions),
            "stability": round(stability, 3),
            "avg_intensity": round(avg_intensity, 3),
            "recent_emotion": emotions[-1] if emotions else "neutral",
        }
