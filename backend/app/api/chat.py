"""
ALAS Chat API — WebSocket + REST endpoints for real-time conversation.

Handles:
- WebSocket streaming chat with memory-augmented responses
- REST endpoint for non-streaming chat
- Session management
"""

import json
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from backend.app.llm.engine import LLMEngine
from backend.app.safety.filter import SafetyFilter
from backend.app.emotion.detector import EmotionDetector

logger = logging.getLogger("alas.api.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Shared instances
_engine: Optional[LLMEngine] = None
_safety: Optional[SafetyFilter] = None
_emotion: Optional[EmotionDetector] = None


def get_engine() -> LLMEngine:
    global _engine
    if _engine is None:
        _engine = LLMEngine()
    return _engine


def get_safety() -> SafetyFilter:
    global _safety
    if _safety is None:
        _safety = SafetyFilter()
    return _safety


def get_emotion() -> EmotionDetector:
    global _emotion
    if _emotion is None:
        _emotion = EmotionDetector()
    return _emotion


# --- REST Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: str = "casual"
    user_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    mode: str
    memory_count: int
    safety_passed: bool
    emotion: Optional[dict] = None


# --- REST Endpoints ---

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and get a complete response (non-streaming)."""
    engine = get_engine()
    safety = get_safety()
    emotion_detector = get_emotion()

    # Detect emotion
    emotion = emotion_detector.detect(request.message)

    # Safety check input
    input_check = safety.check_input(request.message)
    if not input_check["safe"]:
        return ChatResponse(
            response=safety.get_safe_response(input_check.get("reason", "")),
            session_id=request.session_id or str(uuid.uuid4()),
            mode=request.mode,
            memory_count=0,
            safety_passed=False,
        )

    session_id = request.session_id or str(uuid.uuid4())

    try:
        response = await engine.generate(
            message=request.message,
            session_id=session_id,
            mode=request.mode,
            user_id=request.user_id,
        )

        # Safety check output
        output_check = safety.check_output(response)
        if not output_check["safe"]:
            response = safety.get_safe_response(output_check.get("reason", ""))

        # Log implicit feedback
        from backend.app.learning.feedback import get_feedback_tracker
        get_feedback_tracker().log_interaction(session_id, request.message, response, emotion)

        stats = engine.retriever.get_memory_stats()

        return ChatResponse(
            response=response,
            session_id=session_id,
            mode=request.mode,
            memory_count=stats.get("episodic", {}).get("total_memories", 0),
            safety_passed=output_check.get("safe", True),
            emotion=emotion,
        )

    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Check LLM engine health."""
    engine = get_engine()
    return await engine.check_health()


# --- Vision Endpoint ---

@router.post("/vision")
async def analyze_image(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    task: str = Form("describe"),
):
    """
    Analyze an uploaded image using a vision-language model.

    Tasks: describe, ocr, analyze, code
    """
    from backend.app.llm.vision import get_vision_engine

    vision = await get_vision_engine()
    image_data = await image.read()

    result = await vision.analyze_image(
        image_data=image_data,
        prompt=prompt,
        task=task,
    )
    return result


@router.get("/vision/status")
async def vision_status():
    """Check if vision analysis is available."""
    from backend.app.llm.vision import get_vision_engine
    vision = await get_vision_engine()
    return await vision.check_status()


# --- WebSocket Endpoint ---

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming chat.
    
    Protocol:
      Client sends JSON: {"message": "...", "session_id": "...", "mode": "casual"}
      Server streams JSON: {"type": "token", "content": "..."} for each token
      Server sends JSON: {"type": "done", "session_id": "...", "memory_count": N}
      Server sends JSON: {"type": "error", "content": "..."} on error
    """
    await websocket.accept()
    engine = get_engine()
    safety = get_safety()

    logger.info("WebSocket client connected")

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON format",
                })
                continue

            message = data.get("message", "").strip()
            if not message:
                await websocket.send_json({
                    "type": "error",
                    "content": "Empty message",
                })
                continue

            session_id = data.get("session_id", str(uuid.uuid4()))
            mode = data.get("mode", "casual")
            user_id = data.get("user_id", "default")
            conversation_history = data.get("history", [])

            # Safety check input
            input_check = safety.check_input(message)
            if not input_check["safe"]:
                safe_response = safety.get_safe_response()
                await websocket.send_json({
                    "type": "token",
                    "content": safe_response,
                })
                await websocket.send_json({
                    "type": "done",
                    "session_id": session_id,
                    "memory_count": 0,
                    "safety_blocked": True,
                })
                continue

            # Stream response tokens
            try:
                full_response = []
                async for token in engine.generate_stream(
                    message=message,
                    session_id=session_id,
                    mode=mode,
                    user_id=user_id,
                    conversation_history=conversation_history,
                ):
                    full_response.append(token)
                    await websocket.send_json({
                        "type": "token",
                        "content": token,
                    })

                complete = "".join(full_response)

                # Safety check output
                output_check = safety.check_output(complete)
                
                # Log implicit feedback
                from backend.app.learning.feedback import get_feedback_tracker
                get_feedback_tracker().log_interaction(session_id, message, complete, None)

                stats = engine.retriever.get_memory_stats()

                await websocket.send_json({
                    "type": "done",
                    "session_id": session_id,
                    "memory_count": stats.get("episodic", {}).get("total_memories", 0),
                    "safety_blocked": not output_check["safe"],
                })

            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Generation failed: {str(e)}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
