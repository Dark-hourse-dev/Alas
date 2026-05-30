"""
ALAS Semantic Router (Phase 12)

Dynamically routes user prompts to the optimal compute engine.
- Local Engine: For privacy-sensitive, simple, or highly contextual tasks.
- Cloud Engine: For complex reasoning, massive context windows, or heavy coding tasks.
"""
import logging
from typing import Literal

logger = logging.getLogger("alas.llm.router")

class SemanticRouter:
    def __init__(self):
        # Triggers that explicitly demand heavy reasoning
        self.cloud_keywords = {
            "refactor", "complex", "architect", "deep think", 
            "analyze this codebase", "optimization", "algorithm"
        }
        
        # Triggers that explicitly demand local context / privacy
        self.local_keywords = {
            "my name", "my location", "journal", "diary", 
            "remember", "turn off", "home status", "private"
        }

    def route(self, prompt: str) -> Literal["local", "cloud"]:
        """
        Determine the optimal routing destination for the prompt.
        """
        prompt_lower = prompt.lower()
        
        # 1. Privacy / Local Override
        if any(kw in prompt_lower for kw in self.local_keywords):
            logger.info("🚦 Semantic Router: Routing to LOCAL (Privacy/Context Keywords Detected)")
            return "local"
            
        # 2. Complexity / Cloud Override
        if any(kw in prompt_lower for kw in self.cloud_keywords):
            logger.info("🚦 Semantic Router: Routing to CLOUD (Complexity Keywords Detected)")
            return "cloud"
            
        # 3. Length Heuristic
        # If the prompt is very long (e.g. pasting a large file), cloud models handle context better.
        if len(prompt) > 2000:
            logger.info("🚦 Semantic Router: Routing to CLOUD (High Context Length)")
            return "cloud"
            
        # Default to local for zero-cost, zero-latency inference
        logger.info("🚦 Semantic Router: Routing to LOCAL (Default)")
        return "local"

# Global singleton
_router = SemanticRouter()

def get_semantic_router() -> SemanticRouter:
    return _router
