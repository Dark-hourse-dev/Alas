import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.learning.feedback import get_feedback_tracker
from backend.app.learning.evolution import get_evolution_system
import uuid

def fast_simulate():
    print("🧬 ALAS Evolutionary Fast Simulator")
    print("---------------------------------------")
    
    tracker = get_feedback_tracker()
    evolution = get_evolution_system()
    
    initial_genome = dict(evolution.current_genome)
    print(f"Initial Generation: {initial_genome['generation']}")
    print(f"Initial Verbosity: {initial_genome['verbosity_weight']:.2f}")
    
    for i in range(1, 15):
        session_id = f"sim_sess_{i}_{uuid.uuid4().hex[:4]}"
        
        # Inject terrible metrics directly to feedback tracker
        # We simulate that the user was sending very short angry messages,
        # and the AI was rambling on.
        tracker.session_metrics[session_id] = {
            "message_count": 5,
            "user_words": 10,       # user says almost nothing
            "assistant_words": 500, # AI rambling
            "corrections": 3,       # user corrects AI often
            "positive_sentiment_trend": -0.8, # negative emotion
            "task_completions": 0
        }
        
        fitness = tracker.calculate_fitness(session_id)
        
        # Trigger evolution check (it mutates if avg fitness < 0.7 over 5 sessions)
        evolution.evaluate_and_evolve(fitness)
        
        genome = evolution.current_genome
        print(f"[Session {i}] Fitness: {fitness:.2f} | Gen: {genome['generation']} | V: {genome['verbosity_weight']:.2f} F: {genome['formality_index']:.2f} E: {genome['empathy_multiplier']:.2f} P: {genome['proactivity_threshold']:.2f}")

if __name__ == "__main__":
    fast_simulate()
