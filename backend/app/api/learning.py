"""
ALAS Learning API — Endpoints for reflection, evolution, and adapter management.
"""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.app.learning.reflection import get_reflection_engine
from backend.app.learning.evolution import get_evolution_system
from backend.app.learning.lora_manager import get_lora_manager
from backend.app.learning.feedback import get_feedback_tracker
from backend.app.memory.skills import get_skill_memory

router = APIRouter(prefix="/api/learning", tags=["learning"])

class ReflectionRequest(BaseModel):
    session_id: str
    history: List[dict]

class SkillRequest(BaseModel):
    name: str
    description: str
    steps: List[str]

@router.post("/reflect")
async def trigger_reflection(req: ReflectionRequest, background_tasks: BackgroundTasks):
    """Trigger a self-reflection pass on a session history."""
    engine = get_reflection_engine()
    evolution = get_evolution_system()
    feedback = get_feedback_tracker()
    
    # 1. Run reflection in background
    background_tasks.add_task(engine.reflect_on_session, req.session_id, req.history)
    
    # 2. Evolve behavior based on session fitness
    fitness = feedback.calculate_fitness(req.session_id)
    background_tasks.add_task(evolution.evaluate_and_evolve, fitness)
    
    return {"status": "started", "message": "Reflection and evolution tasks queued."}

@router.get("/evolution/status")
async def get_evolution_status():
    """Get the current behavioral genome."""
    evolution = get_evolution_system()
    return evolution.current_genome

@router.get("/feedback/{session_id}")
async def get_feedback_metrics(session_id: str):
    """Get tracking metrics for a session."""
    tracker = get_feedback_tracker()
    return {
        "metrics": tracker.get_metrics(session_id),
        "fitness": tracker.calculate_fitness(session_id)
    }

@router.get("/adapters")
async def list_adapters():
    """List available LoRA adapters and their status."""
    return get_lora_manager().get_registry()

@router.post("/adapters/{name}/load")
async def load_adapter(name: str):
    success = get_lora_manager().load_adapter(name)
    return {"status": "success" if success else "error"}

@router.post("/adapters/{name}/unload")
async def unload_adapter(name: str):
    success = get_lora_manager().unload_adapter(name)
    return {"status": "success" if success else "error"}

@router.post("/skills")
async def add_skill(skill: SkillRequest):
    get_skill_memory().add_skill(skill.name, skill.steps, skill.description)
    return {"status": "success"}

@router.get("/skills/search")
async def search_skills(q: str):
    results = get_skill_memory().search_skills(q)
    return {"results": results}
