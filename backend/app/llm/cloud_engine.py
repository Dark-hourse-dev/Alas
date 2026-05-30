"""
ALAS Cloud Inference Engine (Phase 12)

Fallback cloud reasoning engine for highly complex tasks routed by the Semantic Router.
Uses standard OpenAI-compatible REST API (can point to DeepSeek, OpenAI, Groq, etc.).
"""
import os
import json
import logging
import httpx
from typing import AsyncGenerator, Optional, List, Dict, Any

from backend.app.safety.scrubber import get_scrubber

logger = logging.getLogger("alas.llm.cloud")

class CloudEngine:
    def __init__(self):
        # Defaults to OpenAI standard endpoint, easily configurable via ENV
        self.api_key = os.environ.get("ALAS_CLOUD_API_KEY", "")
        self.api_url = os.environ.get("ALAS_CLOUD_API_URL", "https://api.openai.com/v1/chat/completions")
        self.model = os.environ.get("ALAS_CLOUD_MODEL", "gpt-4o")
        self.scrubber = get_scrubber()

    async def generate_stream(
        self, 
        messages: List[Dict[str, Any]],
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the Cloud LLM, scrubbing outbound PII.
        """
        if not self.api_key:
            yield "\n\n_⚠️ [Cloud Engine] Missing ALAS_CLOUD_API_KEY. Cloud routing failed. Falling back to local..._\n\n"
            return

        # Scrub outbound messages
        scrubbed_messages = []
        for msg in messages:
            scrubbed_msg = msg.copy()
            if isinstance(scrubbed_msg.get("content"), str):
                scrubbed_msg["content"] = self.scrubber.scrub_text(scrubbed_msg["content"])
            scrubbed_messages.append(scrubbed_msg)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": scrubbed_messages,
            "stream": stream
        }

        logger.info(f"☁️ Dispatching request to Cloud Engine ({self.model})...")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if chunk["choices"][0].get("delta", {}).get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"Cloud Engine Error: {e}")
            yield f"\n\n_❌ [Cloud Engine Error]: {e}_\n\n"

# Global singleton
_cloud_engine = CloudEngine()

def get_cloud_engine() -> CloudEngine:
    return _cloud_engine
