"""
ALAS LLM Tools — Standalone Ollama Client (Phase 9.1: Multi-Model Fallback Chain)

Provides reliable LLM completions for internal agents (like Swarm Agents).
Implements a fallback chain: Primary Model -> Fallback Model -> Rule-Based Response.
"""
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("alas.llm.client")

def generate_completion(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    model: Optional[str] = None
) -> str:
    """
    Generate a simple text completion with Multi-Model Fallback (Phase 9).
    This function blocks, so it should be run in a thread if called from asyncio.
    """
    from backend.app.config import get_settings
    import ollama
    
    settings = get_settings()
    primary_model = model or settings.ollama_model
    fallback_model = "phi3" # Lighter fallback model
    
    # Try primary model
    try:
        response = ollama.chat(
            model=primary_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.3}
        )
        return response['message']['content']
    except Exception as e1:
        logger.warning(f"Primary model ({primary_model}) failed: {e1}. Initiating Fallback Chain to {fallback_model}...")
        
        # Try fallback model
        try:
            response = ollama.chat(
                model=fallback_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3}
            )
            return f"[FALLBACK MODE: {fallback_model}] " + response['message']['content']
        except Exception as e2:
            logger.error(f"Fallback model ({fallback_model}) also failed: {e2}. Returning minimal safe response.")
            
            # Rule-based fallback (Graceful Degradation)
            return "ALAS is currently experiencing cognitive subsystem failures. All models are unresponsive. Safe minimal mode engaged."
