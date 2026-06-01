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

    async def generate_complete(
        self,
        messages: List[Dict[str, Any]],
    ) -> str:
        """
        Generate a complete (non-streaming) response from the Cloud LLM.
        """
        if not self.api_key:
            return "[Cloud Engine] Missing ALAS_CLOUD_API_KEY. Cloud routing failed."

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
            "stream": False
        }

        # Phase 18: Autonomous Economics - Check wallet funds
        from backend.app.economics.wallet import get_wallet_manager
        wallet = get_wallet_manager()
        est_cost = 0.05  # Simulated flat cost for a cloud LLM call

        if not wallet.can_afford(est_cost, "USD"):
            logger.warning("💸 Wallet: Insufficient funds for Cloud API. Falling back to local.")
            return "_⚠️ [Economics Engine] Insufficient funds in ALAS Wallet. Cloud routing aborted._"

        logger.info(f"☁️ Dispatching non-streaming request to Cloud Engine ({self.model})...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                
                # Charge the wallet upon success
                wallet.process_payment(est_cost, "USD", recipient="Cloud_API_Provider", reason=f"Cloud Inference: {self.model}")
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Cloud Engine Error: {e}")
            return f"[Cloud Engine Error]: {e}"

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

        # Phase 18: Autonomous Economics - Check wallet funds
        from backend.app.economics.wallet import get_wallet_manager
        wallet = get_wallet_manager()
        est_cost = 0.05

        if not wallet.can_afford(est_cost, "USD"):
            logger.warning("💸 Wallet: Insufficient funds for Cloud API. Falling back to local.")
            yield "\n\n_⚠️ [Economics Engine] Insufficient funds in ALAS Wallet. Cloud routing aborted. Falling back to local..._\n\n"
            return

        logger.info(f"☁️ Dispatching request to Cloud Engine ({self.model})...")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    
                    # Charge the wallet
                    wallet.process_payment(est_cost, "USD", recipient="Cloud_API_Provider", reason=f"Stream Inference: {self.model}")
                    
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
