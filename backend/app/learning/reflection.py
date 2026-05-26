"""
ALAS Self-Reflection Engine.

Runs asynchronously to review recent conversations, evaluate interaction quality,
and extract long-term behavioral insights that are saved to the user profile (L3).
"""

import logging
import asyncio
from typing import List, Dict, Any

from backend.app.config import get_settings
from backend.app.memory.profile import get_profile_store
from backend.app.learning.feedback import get_feedback_tracker
import ollama

logger = logging.getLogger("alas.learning.reflection")

REFLECTION_PROMPT = """You are ALAS, an adaptive AI. You are reflecting on a recent conversation with the user to improve yourself.

Conversation History:
{conversation}

Analyze the interaction and provide a reflection summary in JSON format with exactly these fields:
{{
  "user_insights": ["Insight 1 about what the user likes/wants", "Insight 2..."],
  "behavioral_adjustments": ["How you should change your communication style next time", "..."],
  "suggested_style": "balanced|concise|detailed"
}}

Respond ONLY with valid JSON.
"""

class ReflectionEngine:
    def __init__(self):
        self.settings = get_settings()
        self.client = ollama.AsyncClient(host=self.settings.ollama_host)
        self.profile_store = get_profile_store()
        self.feedback_tracker = get_feedback_tracker()

    async def reflect_on_session(self, session_id: str, conversation_history: List[Dict[str, str]], user_id: str = "default"):
        """
        Run a reflection on the given conversation history.
        Triggered when a session ends or during idle periods.
        """
        if len(conversation_history) < 4:
            logger.info("Session too short for meaningful reflection.")
            return

        # 1. Gather fitness score
        fitness = self.feedback_tracker.calculate_fitness(session_id)
        logger.info(f"Reflecting on session {session_id} (Fitness: {fitness:.2f})")

        # 2. Format conversation for LLM
        convo_text = ""
        for msg in conversation_history:
            role = "User" if msg["role"] == "user" else "ALAS"
            convo_text += f"{role}: {msg['content']}\n\n"

        # Limit to last 2000 chars to avoid massive context
        convo_text = convo_text[-2000:]

        try:
            # 3. Call LLM for reflection
            response = await self.client.chat(
                model=self.settings.ollama_model,
                messages=[{
                    "role": "user",
                    "content": REFLECTION_PROMPT.format(conversation=convo_text)
                }]
            )
            
            result_text = getattr(response.message, "content", "")
            
            import json
            import re
            
            # Extract JSON block
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                reflection_data = json.loads(json_match.group(0))
                
                # 4. Update User Profile (L3) based on reflection
                profile = self.profile_store.get_profile(user_id)
                
                # Update topics/insights
                existing_topics = set(profile.get("topics_of_interest", []))
                new_insights = reflection_data.get("user_insights", [])
                for insight in new_insights:
                    # Very simple heuristic: add as topic if it's short
                    if len(insight.split()) <= 5:
                        existing_topics.add(insight)
                
                profile["topics_of_interest"] = list(existing_topics)
                
                # Update communication style if fitness was low and AI suggested a change
                if fitness < 0.6 and reflection_data.get("suggested_style"):
                    new_style = reflection_data.get("suggested_style")
                    if new_style in ["balanced", "concise", "detailed"]:
                        profile["communication_style"] = new_style
                        logger.info(f"Adapted communication style to: {new_style}")
                
                self.profile_store.update_profile(user_id, **profile)
                logger.info(f"Reflection complete. Extracted {len(new_insights)} insights.")
                
            else:
                logger.warning(f"Failed to parse JSON from reflection response: {result_text}")
                
        except Exception as e:
            logger.error(f"Reflection engine error: {e}")

# Singleton
_reflection_engine = None

def get_reflection_engine() -> ReflectionEngine:
    global _reflection_engine
    if _reflection_engine is None:
        _reflection_engine = ReflectionEngine()
    return _reflection_engine
