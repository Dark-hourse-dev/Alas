import logging
import ollama
from backend.app.config import get_settings

logger = logging.getLogger("alas.cognition.simulator")

async def simulate_outcome(scenario: str, context: str = "") -> str:
    """
    Run a hypothetical text-based simulation to predict causal outcomes.
    This bypasses normal conversational logic to act purely as an objective physics/logic engine.
    """
    system_prompt = """
    You are the ALAS Causal Simulation Sandbox.
    You do not converse. You do not offer opinions.
    You are an objective simulation engine evaluating a hypothetical scenario based on logic, physics, history, and cause-and-effect.
    
    Given a scenario, you must output a structured simulation result containing:
    1. INITIAL STATE: The starting conditions.
    2. PRIMARY EFFECT: The immediate direct consequence.
    3. CASCADING EFFECTS: Secondary and tertiary consequences.
    4. FINAL OUTCOME: The ultimate predicted state of the system.
    5. CONFIDENCE: (Low/Medium/High) based on the predictability of the variables.
    """
    
    prompt = f"Scenario to simulate: {scenario}\nContext/Background: {context}"
    
    logger.info(f"🔮 Running causal simulation on: {scenario}")
    
    try:
        settings = get_settings()
        client = ollama.AsyncClient(host=settings.ollama_host)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        res = await client.chat(
            model=settings.ollama_model,
            messages=messages,
            options={"temperature": 0.3}  # Low temperature for logical consistency
        )
        return res.message.content
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return f"Error running simulation: {e}"
