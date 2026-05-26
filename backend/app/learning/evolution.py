"""
ALAS Behavioral Evolution System.

Maintains a set of behavioral parameters (prompt weights) and evolves them
using a genetic algorithm approach based on fitness scores over many sessions.
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, Any

from backend.app.config import get_settings

logger = logging.getLogger("alas.learning.evolution")

class BehaviorEvolution:
    def __init__(self):
        settings = get_settings()
        self.data_dir = Path(settings.chroma_persist_dir).parent / "learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.genome_file = self.data_dir / "behavior_genome.json"
        
        self.current_genome = self._load_genome()

    def _default_genome(self) -> Dict[str, Any]:
        """Default prompt weights and behavioral thresholds."""
        return {
            "verbosity_weight": 0.5,       # 0 = very terse, 1 = extremely verbose
            "proactivity_threshold": 0.7,  # Confidence required to act proactively
            "formality_index": 0.5,        # 0 = casual slang, 1 = strict professional
            "empathy_multiplier": 1.0,     # How strongly to mirror user emotions
            "generation": 1,
            "fitness_history": []
        }

    def _load_genome(self) -> Dict[str, Any]:
        if self.genome_file.exists():
            try:
                with open(self.genome_file, "r") as f:
                    return json.loads(f.read())
            except Exception as e:
                logger.error(f"Failed to load genome: {e}")
        
        return self._default_genome()

    def _save_genome(self):
        with open(self.genome_file, "w") as f:
            f.write(json.dumps(self.current_genome, indent=2))

    def evaluate_and_evolve(self, session_fitness: float):
        """
        Takes the fitness score from the feedback tracker.
        If fitness is low, we mutate the genome slightly to try to find a better configuration.
        """
        self.current_genome["fitness_history"].append(session_fitness)
        
        # Only evolve if we have enough history for this generation
        if len(self.current_genome["fitness_history"]) >= 5:
            avg_fitness = sum(self.current_genome["fitness_history"]) / 5.0
            logger.info(f"Generation {self.current_genome['generation']} avg fitness: {avg_fitness:.2f}")
            
            # If fitness is below acceptable threshold, mutate!
            if avg_fitness < 0.7:
                logger.info("Fitness below threshold. Mutating behavior genome...")
                self._mutate()
            
            # Reset history and increment generation
            self.current_genome["fitness_history"] = []
            self.current_genome["generation"] += 1
            self._save_genome()

    def _mutate(self):
        """Apply random mutations to behavioral parameters."""
        mutation_rate = 0.15 # +/- 15% change
        
        keys_to_mutate = ["verbosity_weight", "proactivity_threshold", "formality_index", "empathy_multiplier"]
        
        # Pick one random trait to mutate
        target_trait = random.choice(keys_to_mutate)
        
        # Add random noise between -mutation_rate and +mutation_rate
        noise = random.uniform(-mutation_rate, mutation_rate)
        
        new_val = self.current_genome[target_trait] + noise
        # Clamp to 0.0 - 1.0 (except empathy which can go to 2.0)
        max_val = 2.0 if target_trait == "empathy_multiplier" else 1.0
        
        self.current_genome[target_trait] = max(0.0, min(max_val, new_val))
        logger.info(f"Mutated {target_trait} by {noise:+.2f} -> {self.current_genome[target_trait]:.2f}")

    def get_prompt_modifiers(self) -> str:
        """Translates the genome into natural language directives for the system prompt."""
        v = self.current_genome["verbosity_weight"]
        f = self.current_genome["formality_index"]
        
        verbosity_str = "Be very concise and brief." if v < 0.3 else "Give detailed, comprehensive answers." if v > 0.7 else "Keep answers balanced in length."
        formality_str = "Use a casual, relaxed tone." if f < 0.3 else "Use a formal, professional tone." if f > 0.7 else "Use a neutral, polite tone."
        
        return f"{verbosity_str} {formality_str}"

# Singleton
_evolution_system = None

def get_evolution_system() -> BehaviorEvolution:
    global _evolution_system
    if _evolution_system is None:
        _evolution_system = BehaviorEvolution()
    return _evolution_system
