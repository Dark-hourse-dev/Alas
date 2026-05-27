"""
ALAS Task Planner — LLM-based multi-step plan generation.

Converts natural language goals into structured, executable plans:
  User: "Set up a new Python project with FastAPI"
  → Plan with steps: create dir, venv, install, write main.py, init git

The planner uses the LLM to decompose goals and the executor to run them.
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass, field

import ollama

from backend.app.config import get_settings

logger = logging.getLogger("alas.planning.planner")


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_number: int
    description: str
    tool: str  # Which tool to use (e.g., "execute_shell", "write_local_file")
    args: dict  # Arguments for the tool
    rollback_cmd: Optional[str] = None  # Command to undo this step
    requires_approval: bool = False  # Whether this step needs user approval
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """A structured multi-step execution plan."""
    id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    status: str = "draft"  # draft, approved, executing, completed, failed, rolled_back
    current_step: int = 0
    created_at: str = ""
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "tool": s.tool,
                    "status": s.status,
                    "requires_approval": s.requires_approval,
                    "result": s.result[:200] if s.result else None,
                    "error": s.error,
                }
                for s in self.steps
            ],
        }

    def summary(self) -> str:
        """Human-readable plan summary."""
        lines = [f"📋 **Plan: {self.goal}**\n"]
        for s in self.steps:
            icon = {
                "pending": "⬜",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
            }.get(s.status, "⬜")
            approval = " 🔐" if s.requires_approval else ""
            lines.append(f"{icon} Step {s.step_number}: {s.description}{approval}")
        
        completed = sum(1 for s in self.steps if s.status == "completed")
        lines.append(f"\n**Progress:** {completed}/{len(self.steps)} steps completed")
        return "\n".join(lines)


# Available tools that the planner can reference
PLANNABLE_TOOLS = [
    "execute_shell",
    "write_local_file",
    "read_local_file",
    "list_directory",
    "manage_files",
    "search_web",
    "read_webpage",
    "run_code",
    "git_operation",
]


async def generate_plan(goal: str, context: str = "") -> ExecutionPlan:
    """
    Use the LLM to generate a structured execution plan from a natural language goal.
    
    Args:
        goal: The user's goal in natural language.
        context: Additional context (e.g., current directory, project info).
    
    Returns:
        An ExecutionPlan with structured steps.
    """
    import uuid
    from datetime import datetime

    settings = get_settings()
    client = ollama.AsyncClient(host=settings.ollama_host)

    tools_list = ", ".join(PLANNABLE_TOOLS)

    prompt = f"""You are a task planning agent. Given a user's goal, decompose it into a sequence of concrete, executable steps.

Available tools you can use in steps:
- execute_shell: Run a shell command. Args: {{"command": "..."}}
- write_local_file: Write content to a file. Args: {{"filepath": "...", "content": "..."}}
- read_local_file: Read a file. Args: {{"filepath": "..."}}
- list_directory: List directory contents. Args: {{"directory_path": "..."}}
- manage_files: File operations. Args: {{"action": "copy|move|rename|create_dir", "source": "...", "destination": "..."}}
- search_web: Search the internet. Args: {{"query": "..."}}
- read_webpage: Read a URL. Args: {{"url": "..."}}
- run_code: Execute code safely. Args: {{"code": "...", "language": "python|bash"}}
- git_operation: Git operations. Args: {{"operation": "status|diff|log|branch|commit|stash", "repo_path": "..."}}

IMPORTANT RULES:
1. Each step must use exactly ONE tool from the list above.
2. Steps should be atomic — one clear action per step.
3. Include a rollback_cmd (shell command) for destructive steps.
4. Mark steps that modify important data as requires_approval: true.
5. Order steps logically — later steps can depend on earlier ones.

User's goal: {goal}
{f"Additional context: {context}" if context else ""}

Respond with ONLY valid JSON in this exact format:
{{
  "steps": [
    {{
      "step_number": 1,
      "description": "Brief description of what this step does",
      "tool": "tool_name",
      "args": {{"arg1": "value1"}},
      "rollback_cmd": "command to undo this step or null",
      "requires_approval": false
    }}
  ]
}}"""

    try:
        response = await client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )

        raw = response.message.content.strip()
        plan_data = json.loads(raw)

        steps = []
        for s in plan_data.get("steps", []):
            steps.append(PlanStep(
                step_number=s.get("step_number", len(steps) + 1),
                description=s.get("description", ""),
                tool=s.get("tool", "execute_shell"),
                args=s.get("args", {}),
                rollback_cmd=s.get("rollback_cmd"),
                requires_approval=s.get("requires_approval", False),
            ))

        plan = ExecutionPlan(
            id=f"plan_{uuid.uuid4().hex[:10]}",
            goal=goal,
            steps=steps,
            created_at=datetime.now().isoformat(),
        )

        logger.info(f"📋 Generated plan with {len(steps)} steps for: {goal}")
        return plan

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse plan JSON: {e}")
        # Fallback: create a single-step plan
        plan = ExecutionPlan(
            id=f"plan_{uuid.uuid4().hex[:10]}",
            goal=goal,
            steps=[PlanStep(
                step_number=1,
                description=f"Execute goal: {goal}",
                tool="execute_shell",
                args={"command": f"echo 'Plan generation failed for: {goal}'"},
            )],
            created_at=datetime.now().isoformat(),
        )
        return plan

    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        raise
