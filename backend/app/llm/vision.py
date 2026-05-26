"""
ALAS Vision Engine — Multimodal image understanding via Ollama.

Supports image description, visual Q&A, and OCR-like text extraction
using vision-language models (LLaVA, llama3.2-vision, etc.) via Ollama.
Falls back gracefully when no vision model is available.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

import ollama

from backend.app.config import get_settings

logger = logging.getLogger("alas.llm.vision")

# Vision-capable models supported by Ollama
VISION_MODELS = [
    "llava", "llava:7b", "llava:13b", "llava:34b",
    "llama3.2-vision", "llama3.2-vision:11b", "llama3.2-vision:90b",
    "moondream", "moondream2",
    "bakllava",
]

# Default prompts for different vision tasks
VISION_PROMPTS = {
    "describe": "Describe this image in detail. What do you see?",
    "ocr": "Extract and list all text visible in this image. Provide the text exactly as it appears.",
    "analyze": "Analyze this image. What is the main subject? What details are notable?",
    "code": "If this image contains code or a terminal/IDE screenshot, extract and explain the code shown.",
}


class VisionEngine:
    """
    Multimodal vision-language engine.

    Uses Ollama vision models to understand images sent by the user.
    Supports multiple vision tasks: describe, OCR, analyze, visual Q&A.
    """

    def __init__(self):
        settings = get_settings()
        self._client = ollama.AsyncClient(host=settings.ollama_host)
        self._vision_model: Optional[str] = None
        self._available = False

    async def initialize(self):
        """Detect available vision model."""
        try:
            models_resp = await self._client.list()
            if isinstance(models_resp, dict):
                model_list = models_resp.get("models", [])
            else:
                model_list = models_resp.models if hasattr(models_resp, "models") else []

            model_names = []
            for m in model_list:
                if isinstance(m, dict):
                    name = m.get("name", m.get("model", ""))
                else:
                    name = getattr(m, "name", "") or getattr(m, "model", "")
                if name:
                    model_names.append(name)

            # Find first available vision model
            for vm in VISION_MODELS:
                for available in model_names:
                    if vm in available:
                        self._vision_model = available
                        self._available = True
                        logger.info(f"Vision model detected: {self._vision_model}")
                        return

            logger.info("No vision model available. Vision features disabled.")
            logger.info(f"  Available models: {model_names}")
            logger.info(f"  Install one with: ollama pull llava")

        except Exception as e:
            logger.warning(f"Failed to detect vision models: {e}")

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: Optional[str] = None,
        task: str = "describe",
    ) -> dict:
        """
        Analyze an image using a vision-language model.

        Args:
            image_data: Raw image bytes (JPEG, PNG, WebP).
            prompt: Custom prompt for the image. If None, uses task default.
            task: Vision task type: 'describe', 'ocr', 'analyze', 'code'.

        Returns:
            Dictionary with analysis result or error.
        """
        if not self._available:
            await self.initialize()

        if not self._available:
            return {
                "status": "unavailable",
                "error": "No vision model installed. Run: ollama pull llava",
                "suggestion": "Install a vision model to enable image understanding.",
            }

        # Build the prompt
        user_prompt = prompt or VISION_PROMPTS.get(task, VISION_PROMPTS["describe"])

        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        try:
            response = await self._client.chat(
                model=self._vision_model,
                messages=[{
                    "role": "user",
                    "content": user_prompt,
                    "images": [image_b64],
                }],
            )

            content = response.message.content

            return {
                "status": "success",
                "description": content,
                "model": self._vision_model,
                "task": task,
            }

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def check_status(self) -> dict:
        """Check vision engine availability. Always re-checks if unavailable."""
        # Always re-detect if not yet available (model may have been installed)
        await self.initialize()

        return {
            "available": self._available,
            "model": self._vision_model,
            "supported_tasks": list(VISION_PROMPTS.keys()),
            "install_hint": "ollama pull llava" if not self._available else None,
        }


# Module-level singleton
_vision_engine: Optional[VisionEngine] = None


async def get_vision_engine() -> VisionEngine:
    """Get or create the vision engine singleton."""
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = VisionEngine()
        await _vision_engine.initialize()
    return _vision_engine
