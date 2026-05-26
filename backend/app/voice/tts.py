"""
ALAS Text-to-Speech — Edge-TTS powered voice synthesis.

Uses Microsoft Edge TTS for high-quality, expressive speech
synthesis with multiple voice options and emotional styles.
"""

import io
import logging
from typing import Optional

logger = logging.getLogger("alas.voice.tts")


async def synthesize(
    text: str,
    voice: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> bytes:
    """
    Synthesize text to speech audio.
    
    Args:
        text: The text to speak.
        voice: Voice identifier (e.g., 'en-US-AriaNeural').
        rate: Speech rate adjustment (e.g., '+10%', '-20%').
        pitch: Pitch adjustment (e.g., '+5Hz', '-10Hz').
        
    Returns:
        Audio data as bytes (MP3 format).
    """
    try:
        import edge_tts

        if voice is None:
            from backend.app.config import get_settings
            voice = get_settings().tts_voice

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        return b"".join(audio_chunks)

    except ImportError:
        logger.warning("edge-tts not installed. TTS will use browser Speech Synthesis fallback.")
        return b""
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return b""


async def list_voices(language: str = "en") -> list[dict]:
    """
    List available TTS voices for a given language.
    
    Args:
        language: Language prefix to filter (e.g., 'en', 'es', 'fr').
        
    Returns:
        List of voice info dictionaries.
    """
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        filtered = [
            {
                "name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"],
            }
            for v in voices
            if v["Locale"].startswith(language)
        ]
        return filtered
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        return []


# Mode-to-voice-style mapping for adaptive interface
MODE_VOICE_STYLES = {
    "work": {"rate": "+5%", "pitch": "+0Hz"},
    "casual": {"rate": "+0%", "pitch": "+0Hz"},
    "creative": {"rate": "+0%", "pitch": "+5Hz"},
    "learning": {"rate": "-10%", "pitch": "+0Hz"},
    "calm": {"rate": "-15%", "pitch": "-5Hz"},
    "emergency": {"rate": "+15%", "pitch": "+5Hz"},
}


async def synthesize_with_mode(text: str, mode: str = "casual", voice: Optional[str] = None) -> bytes:
    """
    Synthesize speech with mode-adaptive voice styling.
    
    Args:
        text: Text to speak.
        mode: Current interaction mode.
        voice: Override voice identifier.
        
    Returns:
        Audio data as bytes.
    """
    style = MODE_VOICE_STYLES.get(mode, MODE_VOICE_STYLES["casual"])
    return await synthesize(
        text=text,
        voice=voice,
        rate=style["rate"],
        pitch=style["pitch"],
    )
