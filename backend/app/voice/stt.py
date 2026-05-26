"""
ALAS Speech-to-Text — Whisper-based transcription.

Uses faster-whisper for efficient local speech recognition
with word-level timestamps and language detection.
"""

import io
import logging
from typing import Optional

logger = logging.getLogger("alas.voice.stt")

# Lazy-loaded model reference
_whisper_model = None


def _get_model():
    """Lazy-load the Whisper model to avoid startup delay."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            from backend.app.config import get_settings

            settings = get_settings()
            logger.info(f"Loading Whisper model: {settings.whisper_model_size}")
            _whisper_model = WhisperModel(
                settings.whisper_model_size,
                device="auto",
                compute_type="auto",
            )
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.warning(
                "faster-whisper not installed. STT will use browser Web Speech API fallback."
            )
            return None
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            return None
    return _whisper_model


async def transcribe(audio_data: bytes, language: Optional[str] = None) -> dict:
    """
    Transcribe audio data to text.
    
    Args:
        audio_data: Raw audio bytes (WAV/WebM format).
        language: Optional language hint (e.g., 'en').
        
    Returns:
        Dictionary with 'text', 'language', 'segments', and 'duration'.
    """
    model = _get_model()
    if model is None:
        return {
            "text": "",
            "error": "Whisper model not available. Use browser-based STT.",
            "language": language,
        }

    try:
        # faster-whisper accepts file-like objects
        audio_file = io.BytesIO(audio_data)

        segments, info = model.transcribe(
            audio_file,
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
        )

        # Collect all segments
        text_parts = []
        segment_list = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            segment_list.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            })

        return {
            "text": " ".join(text_parts),
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 2),
            "segments": segment_list,
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {
            "text": "",
            "error": str(e),
        }


def is_available() -> bool:
    """Check if Whisper STT is available."""
    return _get_model() is not None
