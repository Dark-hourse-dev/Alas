import logging
from typing import Dict, Any

logger = logging.getLogger("alas.social.tom")

class TheoryOfMindEngine:
    """
    Theory of Mind (ToM) Engine.
    Models the beliefs, knowledge state, and intentions of different users.
    Allows ALAS to track what a user knows versus what ALAS knows.
    """
    def __init__(self):
        # A simple in-memory state tracking for users' beliefs and knowledge.
        self.user_states: Dict[str, Dict[str, Any]] = {}
        logger.info("🧠 Theory of Mind Engine initialized.")
        
    def init_user(self, user_id: str):
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "beliefs": [],
                "known_facts": set(),
                "current_intent": "unknown",
                "emotional_state": "neutral"
            }
            
    def update_intent(self, user_id: str, intent: str):
        """Update the perceived intention of the user's current interaction."""
        self.init_user(user_id)
        self.user_states[user_id]["current_intent"] = intent
        logger.debug(f"Updated intent for {user_id}: {intent}")
        
    def add_known_fact(self, user_id: str, fact: str):
        """Record that the user knows a specific fact (e.g. from previous conversation)."""
        self.init_user(user_id)
        self.user_states[user_id]["known_facts"].add(fact)
        
    def query_user_model(self, user_id: str) -> Dict[str, Any]:
        """Retrieve the ToM model for a user to inject into the LLM prompt."""
        return self.user_states.get(user_id, {})
        
    def generate_tom_prompt_context(self, user_id: str) -> str:
        """Generate a natural language context block describing the user's mental state."""
        state = self.query_user_model(user_id)
        if not state:
            return ""
            
        context = f"[Theory of Mind Context for {user_id}]\n"
        context += f"Perceived Intent: {state.get('current_intent', 'unknown')}\n"
        context += f"Emotional State: {state.get('emotional_state', 'neutral')}\n"
        
        known_facts = list(state.get("known_facts", []))
        if known_facts:
            context += f"Known Facts (Do not over-explain these): {', '.join(known_facts)}\n"
            
        return context
