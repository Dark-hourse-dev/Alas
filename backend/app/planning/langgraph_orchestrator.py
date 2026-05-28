"""
ALAS LangGraph Task Orchestrator (Phase 4.2)

Upgrades the linear planner/executor with a cyclical graph that can 
autonomously backtrack and replan if a step fails.
"""
import json
import logging
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.config import get_settings
from backend.app.planning.planner import PLANNABLE_TOOLS
from backend.app.planning.executor import _execute_step, PlanStep

logger = logging.getLogger("alas.planning.langgraph")


# ---------------------------------------------------------------------------
# 1. Define the Agent State
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    goal: str
    plan: list[dict]
    past_steps: Annotated[list[tuple], operator.add]
    error: str
    current_step_index: int
    max_retries: int
    retries: int


def get_llm():
    """Get the Ollama Chat instance initialized for JSON output."""
    settings = get_settings()
    return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_host, format="json")


# ---------------------------------------------------------------------------
# 2. Define Nodes
# ---------------------------------------------------------------------------
def planner_node(state: AgentState) -> dict:
    """Generates the initial plan."""
    if state.get("plan"):
        return state # Plan already exists, skip
        
    goal = state["goal"]
    logger.info(f"LangGraph Planner: Generating initial plan for '{goal}'")
    
    llm = get_llm()
    prompt = f"""You are an expert task planning agent for ALAS. 
Given the user's goal: {goal}
Decompose it into a JSON array of actionable steps.

Available tools you can use:
- {', '.join(PLANNABLE_TOOLS)}

Output exactly this JSON format:
{{
  "steps": [
    {{
      "tool": "execute_shell", 
      "args": {{"command": "echo hello"}}, 
      "description": "Say hello"
    }}
  ]
}}"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        data = json.loads(response.content)
        plan = data.get("steps", [])
        return {"plan": plan, "current_step_index": 0, "retries": 0, "error": ""}
    except Exception as e:
        logger.error(f"Planner failed to parse JSON: {e}")
        return {"error": f"Failed to generate initial plan: {e}"}


def executor_node(state: AgentState) -> dict:
    """Executes the current step."""
    idx = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    
    if idx >= len(plan):
        return {"error": "No more steps to execute."}
        
    step_data = plan[idx]
    logger.info(f"LangGraph Executor: Running step {idx+1}/{len(plan)} - {step_data.get('description')}")
    
    # Map raw dict back to PlanStep
    step = PlanStep(
        step_number=idx+1,
        description=step_data.get("description", ""),
        tool=step_data.get("tool", "execute_shell"),
        args=step_data.get("args", {})
    )
    
    try:
        result = _execute_step(step)
        logger.info(f"LangGraph Executor: Step {idx+1} succeeded.")
        return {
            "past_steps": [(step_data.get("description"), result)],
            "current_step_index": idx + 1,
            "error": "",
            "retries": 0 # reset retries on success
        }
    except Exception as e:
        logger.error(f"LangGraph Executor: Step {idx+1} failed: {e}")
        return {"error": str(e)}


def replanner_node(state: AgentState) -> dict:
    """Adjusts the plan if an error occurred during execution."""
    error = state.get("error")
    retries = state.get("retries", 0)
    max_retries = state.get("max_retries", 3)
    
    if retries >= max_retries:
        logger.warning("LangGraph Re-planner: Max retries reached. Aborting plan.")
        return {"error": f"Failed after {max_retries} retries. Last error: {error}"}
        
    idx = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    failed_step = plan[idx]
    
    logger.info(f"LangGraph Re-planner: Fixing plan (Retry {retries+1}/{max_retries})")
    
    llm = get_llm()
    prompt = f"""You are a recovery agent. A task plan failed to execute.
Goal: {state['goal']}
Failed Step: {failed_step}
Error Message: {error}

Past successful steps (Do NOT repeat these): 
{state.get('past_steps', [])}

Provide a MODIFIED plan starting from the failed step. Fix the error or use a different tool.
Available tools: {', '.join(PLANNABLE_TOOLS)}
Output exactly this JSON format:
{{
  "steps": [
    {{
      "tool": "...", 
      "args": {{...}}, 
      "description": "..."
    }}
  ]
}}"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        data = json.loads(response.content)
        new_steps = data.get("steps", [])
        
        # Keep successful steps, replace the rest with the new plan
        new_plan = plan[:idx] + new_steps
        return {"plan": new_plan, "error": "", "retries": retries + 1}
    except Exception as e:
        logger.error(f"Re-planner failed to parse JSON: {e}")
        return {"retries": retries + 1}


# ---------------------------------------------------------------------------
# 3. Define Router Edges
# ---------------------------------------------------------------------------
def route_after_planner(state: AgentState):
    if state.get("error"):
        return END
    return "executor"

def route_after_executor(state: AgentState):
    if state.get("error"):
        return "replanner"
    if state.get("current_step_index", 0) >= len(state.get("plan", [])):
        return END
    return "executor"

def route_after_replanner(state: AgentState):
    # If the replanner also errored out (e.g. max retries)
    if state.get("error") and state.get("retries", 0) >= state.get("max_retries", 3):
        return END
    return "executor"


# ---------------------------------------------------------------------------
# 4. Compile Graph
# ---------------------------------------------------------------------------
def create_orchestrator_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)
    
    workflow.set_entry_point("planner")
    
    workflow.add_conditional_edges("planner", route_after_planner, {"executor": "executor", END: END})
    workflow.add_conditional_edges("executor", route_after_executor, {"replanner": "replanner", END: END, "executor": "executor"})
    workflow.add_conditional_edges("replanner", route_after_replanner, {"executor": "executor", END: END})
    
    return workflow.compile()


async def run_langgraph_plan(goal: str) -> dict:
    """
    Entry point to run the LangGraph orchestrator.
    This replaces the legacy planner.py generate_plan + executor.py execute_plan workflow.
    """
    graph = create_orchestrator_graph()
    initial_state = {
        "goal": goal,
        "plan": [],
        "past_steps": [],
        "error": "",
        "current_step_index": 0,
        "max_retries": 3,
        "retries": 0
    }
    
    logger.info("🚀 Starting LangGraph Orchestrator")
    final_state = await graph.ainvoke(initial_state)
    logger.info("🏁 LangGraph Orchestrator Finished")
    
    return final_state
