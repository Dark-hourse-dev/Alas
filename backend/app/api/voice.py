"""
ALAS Voice API — Speech-to-text and text-to-speech endpoints.
"""

from typing import Optional
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from backend.app.voice import stt, tts

router = APIRouter(prefix="/api/voice", tags=["voice"])


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    mode: str = "casual"


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), language: Optional[str] = None):
    """
    Transcribe uploaded audio to text.
    
    Accepts WAV, WebM, or MP3 audio files.
    """
    audio_data = await audio.read()
    result = await stt.transcribe(audio_data, language=language)
    return result


@router.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    Convert text to speech audio.
    
    Returns MP3 audio data.
    """
    audio_data = await tts.synthesize_with_mode(
        text=request.text,
        mode=request.mode,
        voice=request.voice,
    )

    if not audio_data:
        return {"error": "TTS synthesis failed or not available"}

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


@router.get("/voices")
async def list_available_voices(language: str = "en"):
    """List available TTS voices for a language."""
    voices = await tts.list_voices(language)
    return {"voices": voices}


@router.get("/stt/status")
async def stt_status():
    """Check if Whisper STT is available."""
    return {
        "available": stt.is_available(),
        "fallback": "browser_web_speech_api",
    }
