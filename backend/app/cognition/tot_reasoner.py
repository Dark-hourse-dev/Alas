import asyncio
import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
import ollama
from backend.app.config import get_settings

logger = logging.getLogger("alas.cognition.tot")

class ThoughtNode(BaseModel):
    id: str
    content: str
    score: int = 0
    children: List['ThoughtNode'] = []
    is_terminal: bool = False

class ToTReasoner:
    """
    Tree-of-Thoughts (ToT) Reasoner.
    Enables ALAS to explore multiple hypothetical paths, evaluate their logical soundness,
    and backtrack to find the optimal solution to complex problems.
    """
    def __init__(self, max_depth: int = 3, max_branches: int = 3):
        self.max_depth = max_depth
        self.max_branches = max_branches
    
    async def _generate_thoughts(self, context: str, current_thought: str) -> List[str]:
        """Generate N possible next steps/thoughts."""
        prompt = f"""
        Context: {context}
        Current State: {current_thought}
        
        Generate {self.max_branches} distinct, logical next steps or thoughts to progress towards solving the problem.
        Return the result strictly as a JSON array of strings.
        """
        try:
            settings = get_settings()
            client = ollama.AsyncClient(host=settings.ollama_host)
            messages = [
                {"role": "system", "content": "You are a highly logical reasoning engine. Output ONLY a valid JSON array of strings."},
                {"role": "user", "content": prompt}
            ]
            
            res = await client.chat(
                model=settings.ollama_model,
                messages=messages,
                options={"temperature": 0.7}
            )
            response = res.message.content
            
            # Try to parse the JSON array from the response
            # (In production, use structured output if supported)
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx+1]
                thoughts = json.loads(json_str)
                if isinstance(thoughts, list) and len(thoughts) > 0:
                    return thoughts[:self.max_branches]
        except Exception as e:
            logger.error(f"Failed to generate thoughts: {e}")
        
        # Fallback if generation or parsing fails
        return [f"Proceed logically from: {current_thought}"]
        
    async def _evaluate_thought(self, context: str, thought: str) -> int:
        """Evaluate a thought's viability on a scale of 1-10."""
        prompt = f"""
        Context: {context}
        Evaluate this proposed thought/step: "{thought}"
        
        How logical and viable is this step towards solving the problem?
        Return ONLY a single integer from 1 to 10 (1 = completely invalid, 10 = perfect next step).
        """
        try:
            settings = get_settings()
            client = ollama.AsyncClient(host=settings.ollama_host)
            messages = [
                {"role": "system", "content": "You are an objective evaluator. Output ONLY a single integer."},
                {"role": "user", "content": prompt}
            ]
            
            res = await client.chat(
                model=settings.ollama_model,
                messages=messages,
                options={"temperature": 0.1}
            )
            response = res.message.content
            
            # Extract number from response
            import re
            # Extract numbers and filter for valid scores (1-10)
            numbers = re.findall(r'\d+', response)
            valid_scores = [int(n) for n in numbers if 1 <= int(n) <= 10]
            if valid_scores:
                # If multiple numbers found, the score is often the last one (e.g. "Step 1: 8")
                score = valid_scores[-1]
                return score
        except Exception as e:
            logger.error(f"Failed to evaluate thought: {e}")
            
        return 5 # Default mediocre score

    async def reason(self, problem: str) -> Dict[str, Any]:
        """
        Execute the Tree-of-Thoughts reasoning process.
        """
        logger.info(f"🧠 Starting ToT Reasoning for: {problem}")
        
        root = ThoughtNode(id="root", content=problem, score=10)
        best_path = []
        
        # Simple BFS expansion for prototyping
        queue = [(root, 0, [])] # path_history stores list of dicts
        
        while queue:
            current_node, depth, path_history = queue.pop(0)
            current_path = path_history + [{'thought': current_node.content, 'score': current_node.score}]
            
            if depth >= self.max_depth:
                if not best_path or current_node.score > best_path[-1]['score']:
                    best_path = current_path
                continue
                
            # Generate branches
            context = "\n".join([step['thought'] for step in current_path])
            new_thoughts = await self._generate_thoughts(problem, context)
            
            for i, thought in enumerate(new_thoughts):
                score = await self._evaluate_thought(problem, thought)
                child_node = ThoughtNode(
                    id=f"{current_node.id}-{i}",
                    content=thought,
                    score=score
                )
                current_node.children.append(child_node)
                
                # Only explore promising paths (Pruning)
                if score >= 6:
                    queue.append((child_node, depth + 1, current_path))
                    
        return {
            "problem": problem,
            "best_path": best_path,
            "final_conclusion": best_path[-1]['thought'] if best_path else "Could not reach a logical conclusion."
        }
