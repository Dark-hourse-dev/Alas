"""
ALAS Tool Registry — Agentic action capabilities.

Defines the tools available to the LLM and handles their execution.
Tools are formatted as JSON schemas compatible with Ollama's tool calling API.
"""

import datetime
import json
import logging
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Callable
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger("alas.llm.tools")

# --- Tool Implementations ---

def get_current_time(timezone: str = "local") -> str:
    """Get the current time and date."""
    now = datetime.datetime.now()
    return f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}."


def get_weather(location: str) -> str:
    """
    Get the current weather for a specific location.
    (Currently a simulated mock tool for safety).
    """
    # In a real app, this would call OpenWeatherMap or similar.
    mock_data = {
        "london": "15°C, Light Rain",
        "new york": "22°C, Partly Cloudy",
        "tokyo": "28°C, Clear Skies",
        "sydney": "18°C, Windy",
        "paris": "19°C, Sunny"
    }
    loc = location.lower()
    for key, value in mock_data.items():
        if key in loc:
            return f"The current weather in {location.title()} is {value}."
    return f"Weather data for {location} is currently unavailable. Assume it's a mild day."


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Extremely basic and safe evaluator
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in math expression. Only basic arithmetic is allowed."
        
        # pylint: disable=eval-used
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error calculating expression: {e}"


def read_local_file(filepath: str) -> str:
    """Read the contents of a local text file."""
    try:
        path = Path(filepath).resolve()
        
        # Security constraint: only allow reading files within the workspace for now, or safe directories.
        # For this prototype, we'll just restrict large files.
        if not path.exists():
            return f"Error: File not found at {filepath}"
        
        if path.stat().st_size > 50000:  # 50KB limit
            return f"Error: File is too large to read (> 50KB)."
            
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_local_file(filepath: str, content: str) -> str:
    """Write content to a local file."""
    try:
        path = Path(filepath).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_directory(directory_path: str) -> str:
    """List the contents of a directory."""
    try:
        path = Path(directory_path).resolve()
        if not path.exists() or not path.is_dir():
            return f"Error: Directory not found at {directory_path}"
        
        items = []
        for item in path.iterdir():
            type_str = "DIR" if item.is_dir() else "FILE"
            items.append(f"[{type_str}] {item.name}")
            
        if not items:
            return f"Directory {directory_path} is empty."
            
        return "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {e}"


def execute_reminder(message: str, minutes_from_now: int) -> str:
    """Schedule a reminder via the ALAS Scheduler."""
    try:
        from datetime import datetime, timedelta
        from backend.app.proactive.scheduler import get_scheduler
        
        run_at = datetime.now() + timedelta(minutes=minutes_from_now)
        task_id = get_scheduler().add_reminder(message, run_at)
        
        return f"Reminder set successfully! It will trigger at {run_at.strftime('%I:%M %p')}. Task ID: {task_id}"
    except Exception as e:
        logger.error(f"Failed to set reminder: {e}")
        return f"Error setting reminder: {e}"

def execute_add_skill(skill_name: str, description: str, steps: list) -> str:
    """Save a new procedural skill to ALAS Skill Memory."""
    from backend.app.memory.skills import get_skill_memory
    try:
        get_skill_memory().add_skill(skill_name, steps, description)
        return f"Successfully learned and saved skill: {skill_name}"
    except Exception as e:
        import logging
        logging.getLogger("alas.tools").error(f"Failed to save skill: {e}")
        return f"Failed to save skill: {e}"

def execute_search_skills(query: str) -> str:
    """Search ALAS Skill Memory for previously learned skills."""
    from backend.app.memory.skills import get_skill_memory
    try:
        results = get_skill_memory().search_skills(query)
        if not results:
            return "No matching skills found in memory."
        
        output = []
        for r in results:
            output.append(f"Skill: {r['name']}\nDescription: {r['description']}\nSteps:\n" + "\n".join(f"- {s}" for s in r['steps']))
        return "\n\n".join(output)
    except Exception as e:
        return f"Failed to search skills: {e}"

def execute_shell(command: str) -> str:
    """
    Execute a shell command with Permission Tier safety checks.
    
    🟢 AUTO   — Executes silently (ls, cat, git status, etc.)
    🟡 NOTIFY — Executes and logs a notification (pip install, git push, etc.)
    🔴 ASK    — BLOCKED until user explicitly approves (rm, sudo, etc.)
    """
    from backend.app.safety.permissions import get_permission_manager, PermissionTier

    pm = get_permission_manager()
    allowed, tier, reason = pm.is_allowed(command)

    if not allowed:
        # 🔴 ASK tier — block execution
        logger.warning(f"🔴 BLOCKED shell command (tier={tier.value}): {command} — {reason}")
        pm.log_action(command, tier.value, "BLOCKED", approved_by="system")
        return (
            f"⛔ PERMISSION DENIED — This command requires explicit user approval.\n"
            f"Command: {command}\n"
            f"Tier: 🔴 ASK\n"
            f"Reason: {reason}\n\n"
            f"Tell the user what you want to do and ask them to approve it via the "
            f"ALAS permissions panel, or suggest a safer alternative."
        )

    # 🟢 AUTO or 🟡 NOTIFY — execute
    tier_icon = "🟢" if tier == PermissionTier.AUTO else "🟡"
    logger.info(f"{tier_icon} Executing shell command (tier={tier.value}): {command}")

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n--- STDERR ---\n{result.stderr}"

        if not output.strip():
            output = f"Command executed (Return code: {result.returncode}), no output."

        # Truncate if too long (LLM context window protection)
        if len(output) > 4000:
            output = output[:4000] + "\n...[Output truncated due to length]..."

        # Log the action
        pm.log_action(command, tier.value, output, approved_by="auto")

        # 🟡 NOTIFY tier — prepend a notice
        if tier == PermissionTier.NOTIFY:
            output = f"🟡 [NOTIFY] Executed: `{command}`\n\n{output}"

        return output
    except subprocess.TimeoutExpired:
        pm.log_action(command, tier.value, "TIMEOUT", approved_by="auto")
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        pm.log_action(command, tier.value, f"ERROR: {e}", approved_by="auto")
        return f"Error executing shell command: {e}"


def get_system_info() -> str:
    """Get a snapshot of current system resource usage."""
    import shutil
    import platform
    import os

    info_parts = []

    # OS info
    info_parts.append(f"OS: {platform.system()} {platform.release()}")
    info_parts.append(f"Architecture: {platform.machine()}")
    info_parts.append(f"Hostname: {platform.node()}")

    # CPU
    try:
        load1, load5, load15 = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        info_parts.append(f"CPU Cores: {cpu_count}")
        info_parts.append(f"Load Average: {load1:.2f} / {load5:.2f} / {load15:.2f}")
    except Exception:
        pass

    # Memory
    try:
        result = subprocess.run(
            "free -h | head -2", shell=True, capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            info_parts.append(f"Memory:\n{result.stdout.strip()}")
    except Exception:
        pass

    # Disk
    try:
        usage = shutil.disk_usage("/")
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        info_parts.append(
            f"Disk (/): {used_gb:.1f}GB used / {total_gb:.1f}GB total ({free_gb:.1f}GB free)"
        )
    except Exception:
        pass

    # GPU (nvidia-smi)
    try:
        result = subprocess.run(
            "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu "
            "--format=csv,noheader,nounits",
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            info_parts.append(f"GPU: {result.stdout.strip()}")
    except Exception:
        pass

    # Uptime
    try:
        result = subprocess.run("uptime -p", shell=True, capture_output=True, text=True, timeout=5)
        if result.stdout:
            info_parts.append(f"Uptime: {result.stdout.strip()}")
    except Exception:
        pass

    return "\n".join(info_parts)


def execute_get_user_state() -> str:
    """Get the live user state (presence, emotion, attention) from the webcam sensor."""
    from backend.app.sensors.webcam import get_webcam_sensor
    import time
    
    from backend.app.sensors.mic import get_mic_sensor
    
    webcam_sensor = get_webcam_sensor()
    mic_sensor = get_mic_sensor()
    
    webcam_state = webcam_sensor.get_state()
    mic_state = mic_sensor.get_state()
    
    if webcam_state.get("error"):
        return f"Webcam sensor error: {webcam_state['error']}"
        
    if not webcam_state.get("user_present"):
        presence = "User is not currently visible to the webcam."
    else:
        presence = (
            f"**User Presence**: Detected\n"
            f"**Attention**: {webcam_state.get('attention', 'unknown').capitalize()}\n"
            f"**Emotion**: {webcam_state.get('emotion', 'neutral').capitalize()}"
        )
        
    age = time.time() - webcam_state.get("last_updated", 0)
    
    speaking = "Yes" if mic_state.get("is_speaking") else "No"
    vol = mic_state.get("volume", 0.0)
    
    return (
        f"{presence}\n"
        f"**Currently Speaking**: {speaking} (Volume: {vol:.3f})\n"
        f"*(Visual data is {age:.1f} seconds old)*"
    )


def execute_system_control(action: str, value: str = "") -> str:
    """Control OS settings like volume, brightness, or launch apps."""
    from backend.app.safety.permissions import get_permission_manager
    pm = get_permission_manager()
    
    if action == "volume":
        cmd = f"amixer -D pulse sset Master {value}%"
    elif action == "brightness":
        cmd = f"brightnessctl set {value}%"
    elif action == "open_app":
        # Launch app in background safely without blocking
        cmd = f"nohup {value} > /dev/null 2>&1 &"
    else:
        return f"Unknown system control action: {action}"
        
    allowed, tier, reason = pm.is_allowed(cmd)
    if not allowed:
        return f"⛔ PERMISSION DENIED: {reason}"
        
    try:
        subprocess.run(cmd, shell=True, check=True)
        pm.log_action(cmd, tier.value, "OK", approved_by="auto")
        return f"🟢 System control '{action}' executed successfully."
    except Exception as e:
        return f"Error executing system control '{action}': {e}"


def execute_read_clipboard() -> str:
    """Read the current content of the system clipboard."""
    try:
        # Try wayland first
        result = subprocess.run(["wl-paste"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
            
        # Fallback to xclip
        result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return result.stdout.strip()
            
        return "Clipboard is empty or unsupported on this display server."
    except Exception as e:
        return f"Error reading clipboard: {e}"


def execute_analyze_screen(prompt: str = "") -> str:
    """Take a screenshot of the user's screen and analyze it with ALAS Vision."""
    import tempfile
    import asyncio
    
    try:
        from PIL import ImageGrab
        # Requires scrot or xcb on Linux
        img = ImageGrab.grab(all_screens=True)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            with open(tmp.name, "rb") as f:
                image_bytes = f.read()
    except Exception as e:
        return f"Failed to capture screen (Make sure scrot is installed if on Linux): {e}"
        
    try:
        from backend.app.llm.vision import get_vision_engine
        
        async def run_vision():
            engine = await get_vision_engine()
            return await engine.analyze_image(image_bytes, prompt, task="analyze")
            
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = pool.submit(lambda: asyncio.run(run_vision())).result(timeout=60)
        else:
            res = asyncio.run(run_vision())
            
        if res.get("status") == "success":
            return f"👀 Screen Analysis:\n{res.get('description')}"
        else:
            return f"Vision Error: {res.get('error')}"
    except Exception as e:
        return f"Failed to analyze screen: {e}"


def execute_send_notification(title: str, message: str) -> str:
    """Send a system-level desktop notification to the user."""
    try:
        subprocess.run(["notify-send", title, message], check=False)
        return "Notification sent successfully."
    except FileNotFoundError:
        return "notify-send command not found on this OS."
    except Exception as e:
        return f"Failed to send notification: {e}"


def execute_browser_action(url: str, action: str, selector: str = "", text: str = "") -> str:
    """Execute a single browser action synchronously."""
    from backend.app.tools.browser_agent import execute_browser_action as _browser_action
    return _browser_action(url, action, selector, text)


def process_document(file_path: str) -> str:
    from backend.app.tools.data_agent import process_document as _process_document
    return _process_document(file_path)

def query_database(db_uri: str, query: str) -> str:
    from backend.app.tools.data_agent import query_database as _query_database
    return _query_database(db_uri, query)


def get_home_status(entity_id: str = "") -> str:
    from backend.app.tools.iot_agent import get_home_status as _get_home_status
    return _get_home_status(entity_id)

def control_home_device(entity_id: str, action: str, parameters: dict = None) -> str:
    from backend.app.tools.iot_agent import control_home_device as _control_home_device
    return _control_home_device(entity_id, action, parameters)

def publish_mqtt_message(topic: str, message: str) -> str:
    from backend.app.tools.iot_agent import publish_mqtt_message as _publish_mqtt_message
    return _publish_mqtt_message(topic, message)


def manage_files(action: str, source: str, destination: str = "") -> str:
    """
    Perform file management operations with permission checks.
    Actions: copy, move, rename, create_dir, list_tree
    """
    from backend.app.safety.permissions import get_permission_manager

    pm = get_permission_manager()
    src = Path(source).resolve()

    if action == "list_tree":
        # Safe, auto-tier
        try:
            if not src.exists():
                return f"Error: Path not found: {source}"
            items = []
            for item in sorted(src.rglob("*")):
                rel = item.relative_to(src)
                depth = len(rel.parts) - 1
                if depth > 3:  # Limit depth
                    continue
                prefix = "  " * depth
                icon = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    sz = item.stat().st_size
                    size = f" ({sz:,} bytes)" if sz < 1_000_000 else f" ({sz / 1_000_000:.1f} MB)"
                items.append(f"{prefix}{icon} {item.name}{size}")
            return "\n".join(items[:200]) or "Empty directory."
        except Exception as e:
            return f"Error: {e}"

    elif action == "create_dir":
        try:
            src.mkdir(parents=True, exist_ok=True)
            pm.log_action(f"mkdir -p {source}", "notify", "OK")
            return f"🟡 Created directory: {source}"
        except Exception as e:
            return f"Error creating directory: {e}"

    elif action in ("copy", "move", "rename"):
        if not destination:
            return "Error: destination is required for copy/move/rename."
        dst = Path(destination).resolve()
        cmd_map = {"copy": f"cp -r '{src}' '{dst}'", "move": f"mv '{src}' '{dst}'", "rename": f"mv '{src}' '{dst}'"}
        cmd = cmd_map[action]
        allowed, tier, reason = pm.is_allowed(cmd)
        if not allowed:
            return f"⛔ PERMISSION DENIED for {action}: {reason}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            pm.log_action(cmd, tier.value, result.stdout or "OK")
            return f"{'🟡' if tier.value == 'notify' else '🟢'} {action.title()} complete: {source} → {destination}"
        except Exception as e:
            return f"Error: {e}"

    return f"Unknown action: {action}. Supported: copy, move, rename, create_dir, list_tree"


def search_web(query: str) -> str:
    """Search the web for a query and return top results."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No web results found."
        
        output = []
        for r in results:
            output.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Web search failed: {e}"


def read_webpage(url: str) -> str:
    """Read and extract text from a webpage."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ALASBot/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            
        soup = BeautifulSoup(html, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        # Truncate to save context
        if len(text) > 4000:
            return text[:4000] + "\n...[Content truncated]"
        return text
    except Exception as e:
        return f"Failed to read webpage: {e}"


# --- Phase 4 Tool Implementations ---

def execute_run_code(code: str, language: str = "python") -> str:
    """Execute code in the ALAS sandbox."""
    from backend.app.sandbox.executor import run_code
    result = run_code(code=code, language=language)
    return result.to_str()


def execute_git_operation(operation: str, repo_path: str = ".", **kwargs) -> str:
    """Execute a git operation."""
    from backend.app.tools.git_agent import git_operation
    return git_operation(operation=operation, repo_path=repo_path, **kwargs)


def execute_research_topic(topic: str, depth: str = "standard") -> str:
    """Run autonomous research on a topic."""
    from backend.app.tools.research_agent import research_topic
    return research_topic(topic=topic, depth=depth)


def execute_create_plan(goal: str) -> str:
    """Create and automatically execute a multi-step execution plan using LangGraph."""
    import asyncio
    from backend.app.planning.langgraph_orchestrator import run_langgraph_plan

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                final_state = pool.submit(
                    lambda: asyncio.run(run_langgraph_plan(goal))
                ).result(timeout=600)  # Extended timeout for full execution
        else:
            final_state = asyncio.run(run_langgraph_plan(goal))

        if final_state.get("error"):
            return f"❌ Plan execution failed:\n{final_state['error']}\n\nPast successful steps:\n" + "\n".join(
                [f"- {step[0]}: {step[1]}" for step in final_state.get("past_steps", [])]
            )

        output = ["✅ Plan executed successfully using LangGraph!"]
        for step_desc, result in final_state.get("past_steps", []):
            output.append(f"**Step**: {step_desc}\n**Result**: {result}\n")

        return "\n".join(output)
    except Exception as e:
        return f"Failed to execute plan via LangGraph: {e}"


def execute_submit_background_task(name: str, task_type: str, params: str = "{}") -> str:
    """Submit a task to the background queue."""
    from backend.app.tasks.queue import get_task_queue

    try:
        parsed_params = json.loads(params) if isinstance(params, str) else params
    except json.JSONDecodeError:
        parsed_params = {}

    queue = get_task_queue()
    task_id = queue.submit(
        name=name,
        task_type=task_type,
        description=f"Background: {name}",
        params=parsed_params,
    )
    return f"✅ Background task submitted!\n**Task ID:** `{task_id}`\n**Name:** {name}\n**Type:** {task_type}\n\nThe task is running in the background. I'll notify you when it completes."


# --- Integrations (Phase 4.5) ---
def execute_analyze_code(file_path: str) -> str:
    from backend.app.tools.integrations import analyze_code
    return analyze_code(file_path)

def execute_transcribe_audio(file_path: str) -> str:
    from backend.app.tools.integrations import transcribe_audio
    return transcribe_audio(file_path)

def execute_cloud_sync(action: str, target: str) -> str:
    from backend.app.tools.integrations import cloud_sync
    return cloud_sync(action, target)

def execute_track_time(task_name: str, duration_minutes: int) -> str:
    from backend.app.tools.integrations import track_time
    return track_time(task_name, duration_minutes)

def execute_visualize_data(dataset_info: str) -> str:
    from backend.app.tools.integrations import visualize_data
    return visualize_data(dataset_info)


# --- Phase 7 (Embodied Intelligence) ---
def execute_simulate_physics(scenario: str) -> str:
    from backend.app.embodied.physics_sim import simulate_physics
    return simulate_physics(scenario)

def execute_drone_action(action: str, **kwargs) -> str:
    from backend.app.embodied.drone_agent import execute_drone_command
    return execute_drone_command(action, **kwargs)


# --- Phase 8 (Social & Swarm Intelligence) ---
def execute_dispatch_swarm_task(task_type: str, payload_json: str) -> str:
    """Dispatch a task to the Swarm blackboard and wait for consensus."""
    import asyncio
    import json
    from backend.app.swarm.blackboard import Blackboard
    from backend.app.swarm.meta_agent import MetaAgent
    from backend.app.swarm.sub_agents import initialize_swarm
    
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return "Error: payload_json must be valid JSON."
        
    async def run_swarm():
        bb = Blackboard()
        meta = MetaAgent(bb)
        agents = initialize_swarm(bb)
        for name, ag in agents.items():
            meta.register_agent(name, ag)
            
        # Dispatch task based on type (e.g., 'code' or 'safety_check')
        await meta.dispatch_task(task_type, payload)
        
        # Wait for consensus or result
        for _ in range(30): # Wait up to 30 seconds
            await asyncio.sleep(1)
            # Depending on task type, we check the corresponding result topic
            result_topic = f"task_{task_type}_result"
            if task_type == 'safety_check':
                result_topic = 'safety_check_result'
                
            state = bb.read_state(result_topic)
            if state:
                latest = state[-1]['data']
                return f"🐝 **Swarm Agent [{latest.get('agent', 'Unknown')}] responded:**\n{latest.get('response', latest.get('explanation', 'Done'))}"
                
        return "Swarm timeout: No agents responded in time."

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(run_swarm())).result(timeout=45)
        else:
            return asyncio.run(run_swarm())
    except Exception as e:
        return f"Swarm error: {e}"


# --- Phase 9 (Infrastructure Fortress) ---
def execute_system_snapshot(reason: str = "manual") -> str:
    from backend.app.safety.fortress import execute_system_snapshot
    return execute_system_snapshot(reason)

def execute_heal_memory() -> str:
    from backend.app.safety.fortress import execute_heal_memory
    return execute_heal_memory()


# --- Phase 10 (Meta-Intelligence) ---
def execute_trigger_dream() -> str:
    from backend.app.cognition.dream import execute_dream_cycle
    return execute_dream_cycle()

def execute_self_improvement() -> str:
    from backend.app.learning.lora_trainer import execute_self_improvement
    return execute_self_improvement()


# --- Phase 5 (Cognitive Superpowers) ---
def execute_deep_think(problem: str) -> str:
    import asyncio
    from backend.app.cognition.tot_reasoner import ToTReasoner
    
    try:
        reasoner = ToTReasoner(max_depth=3, max_branches=3)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    lambda: asyncio.run(reasoner.reason(problem))
                ).result(timeout=120)
        else:
            result = asyncio.run(reasoner.reason(problem))
            
        output = f"🧠 **Deep Thought Process for:** {problem}\n\n"
        for i, node in enumerate(result['best_path']):
            output += f"**Step {i+1}** (Score: {node['score']}/10): {node['thought']}\n"
        output += f"\n**Conclusion:** {result['final_conclusion']}"
        return output
    except Exception as e:
        return f"Deep thought failed: {e}"

def execute_simulate_outcome(scenario: str, context: str = "") -> str:
    import asyncio
    from backend.app.cognition.simulator import simulate_outcome
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    lambda: asyncio.run(simulate_outcome(scenario, context))
                ).result(timeout=60)
        else:
            result = asyncio.run(simulate_outcome(scenario, context))
        return result
    except Exception as e:
        return f"Simulation failed: {e}"


# --- Tool Registry Mapping ---
# Maps the tool name (from LLM) to the actual Python function
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "calculate": calculate,
    "execute_shell": execute_shell,
    "get_system_info": get_system_info,
    "get_user_state": execute_get_user_state,
    "system_control": execute_system_control,
    "read_clipboard": execute_read_clipboard,
    "analyze_screen": execute_analyze_screen,
    "send_notification": execute_send_notification,
    "browser_action": execute_browser_action,
    "process_document": process_document,
    "get_home_status": get_home_status,
    "control_home_device": control_home_device,
    "publish_mqtt_message": publish_mqtt_message,
    "search_web": search_web,
    "read_webpage": read_webpage,
    "set_reminder": execute_reminder,
    "add_skill": execute_add_skill,
    "search_skills": execute_search_skills,
    # Phase 4 — Agentic Autonomy
    "run_code": execute_run_code,
    "research_topic": execute_research_topic,
    "create_plan": execute_create_plan,
    "submit_background_task": execute_submit_background_task,
    # Phase 4.5 — Integrations
    "analyze_code": execute_analyze_code,
    "transcribe_audio": execute_transcribe_audio,
    "cloud_sync": execute_cloud_sync,
    "track_time": execute_track_time,
    "visualize_data": execute_visualize_data,
    # Phase 7 — Embodied Intelligence
    "simulate_physics": execute_simulate_physics,
    "drone_action": execute_drone_action,
    # Phase 8 — Swarm Intelligence
    "dispatch_swarm_task": execute_dispatch_swarm_task,
    # Phase 9 — Infrastructure Fortress
    "system_snapshot": execute_system_snapshot,
    "heal_memory": execute_heal_memory,
    # Phase 10 — Meta-Intelligence
    "trigger_dream": execute_trigger_dream,
    "self_improve": execute_self_improvement,
    # Phase 5 — Cognitive Superpowers
    "deep_think": execute_deep_think,
    "simulate_outcome": execute_simulate_outcome,
}

# --- Ollama Tool Schemas ---
# This is what gets passed to the Ollama API in the `tools` parameter.
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time. Useful when you need to know what time it is, what day it is, or relative time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "The timezone to get the time for, e.g., 'local', 'UTC'."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a specific city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state/country, e.g., 'San Francisco, CA' or 'London, UK'"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression. Use this for math questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A mathematical expression to evaluate, using basic operators (+, -, *, /)."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": "Read the contents of a local text file. Use this when the user asks you to read or analyze a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The absolute or relative path to the file to read."
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_local_file",
            "description": "Write or overwrite content to a local file. Use this to create files, write code, or save information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The absolute or relative path to the file to write."
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write into the file."
                    }
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List all files and folders in a given directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "The path to the directory to list."
                    }
                },
                "required": ["directory_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a shell command (Bash/Terminal) on the host system. Commands are checked against a 3-tier permission system: safe commands run automatically, moderate commands run with notification, dangerous commands require user approval. Use this to install packages, run scripts, manage git, check system status, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get a comprehensive snapshot of system resources: OS info, CPU cores and load, RAM usage, disk space, GPU status (if available), and uptime. Use this when the user asks about system status, performance, or resource usage.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_state",
            "description": "Get the live physical state of the user via webcam sensors (presence, attention, basic emotion). Use this to see if the user is happy, stressed, distracted, or currently away from their computer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_control",
            "description": "Control system settings like volume, brightness, or launch applications. Use this to adjust the computer's physical state or open software for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'volume', 'brightness', or 'open_app'."
                    },
                    "value": {
                        "type": "string",
                        "description": "The value for the action. For volume/brightness, use a percentage (e.g., '50'). For open_app, use the executable name (e.g., 'code' or 'firefox')."
                    }
                },
                "required": ["action", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_clipboard",
            "description": "Read the current text content of the user's system clipboard. Use this when the user asks you to 'read what I copied' or 'explain my clipboard'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_screen",
            "description": "Take a screenshot of the user's current screen and analyze it using the Vision Engine. Use this when the user asks 'what is on my screen' or wants you to read something they are looking at.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Optional specific question about the screen (e.g., 'What error message is shown?')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Send a system-level desktop notification to the user. Use this to alert them when a background task finishes or to send a proactive message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the notification."
                    },
                    "message": {
                        "type": "string",
                        "description": "The body message of the notification."
                    }
                },
                "required": ["title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_action",
            "description": "Execute a dynamic browser action (navigate, click, fill, extract) using a headless browser. Use this to interact with dynamic sites, login portals, or complex web apps. Always provide the URL of the page you are acting upon, as the browser restores session cookies but needs the URL to reload the DOM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the page to act upon. REQUIRED."
                    },
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'navigate', 'click', 'fill', or 'extract'."
                    },
                    "selector": {
                        "type": "string",
                        "description": "The CSS selector for the element to click or fill (e.g., 'button#login', 'input[name=\"password\"]')."
                    },
                    "text": {
                        "type": "string",
                        "description": "The text to type into the element (used only for 'fill' action)."
                    }
                },
                "required": ["url", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_document",
            "description": "Extract text and data from complex documents including PDFs, Word documents (.docx), and Excel spreadsheets (.xlsx, .csv). Use this when the user asks you to read or summarize a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the document to process."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Execute a read-only SQL query against a database. Use this to analyze data stored in SQLite, PostgreSQL, or MySQL databases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "db_uri": {
                        "type": "string",
                        "description": "The SQLAlchemy connection URI (e.g., 'sqlite:///data.db' or 'postgresql://user:pass@localhost/db')."
                    },
                    "query": {
                        "type": "string",
                        "description": "The raw SQL SELECT query to execute."
                    }
                },
                "required": ["db_uri", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_home_status",
            "description": "Get the status of smart home devices or sensors from Home Assistant. If entity_id is not specified, returns a list of active devices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The specific Home Assistant entity ID (e.g. 'light.living_room' or 'sensor.temperature'). Leave blank for overall summary."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_home_device",
            "description": "Control a smart home device connected to Home Assistant. Allows turning on/off switches, adjusting light brightness, setting thermostats, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The Home Assistant entity ID (e.g., 'light.kitchen')."
                    },
                    "action": {
                        "type": "string",
                        "description": "The action to perform (e.g., 'turn_on', 'turn_off', 'toggle', 'set_temperature')."
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Optional key-value parameters for the action (e.g. {'brightness': 150} or {'temperature': 22.5})."
                    }
                },
                "required": ["entity_id", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "publish_mqtt_message",
            "description": "Publish a message to an MQTT broker. Useful for raw sensor triggers or custom DIY automations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The MQTT topic (e.g., 'home/living_room/light')."
                    },
                    "message": {
                        "type": "string",
                        "description": "The message body to publish (usually a string or JSON string)."
                    }
                },
                "required": ["topic", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_files",
            "description": "Perform file management operations: copy, move, rename files/folders, create directories, or list a directory tree. Use this for organizing files, creating project structures, or exploring file systems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The operation to perform: 'copy', 'move', 'rename', 'create_dir', or 'list_tree'."
                    },
                    "source": {
                        "type": "string",
                        "description": "The source file/directory path."
                    },
                    "destination": {
                        "type": "string",
                        "description": "The destination path (required for copy, move, rename; not needed for create_dir, list_tree)."
                    }
                },
                "required": ["action", "source"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the internet for real-time information, news, or answers to questions. Returns a list of URLs and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the internet."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Read and extract the text content from a specific URL. Use this to read articles found via search_web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the webpage to read."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a one-time reminder for the user. ALAS will send a desktop notification when the time arrives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The reminder message to display to the user."
                    },
                    "minutes_from_now": {
                        "type": "integer",
                        "description": "How many minutes from now to trigger the reminder."
                    }
                },
                "required": ["message", "minutes_from_now"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_skill",
            "description": "Permanently save a new skill or topic to your persistent memory. Use this after you search the web to learn something new.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "A short, memorable name for the skill/topic (e.g., 'Biotech Devices', 'Python Generators')."
                    },
                    "description": {
                        "type": "string",
                        "description": "A thorough summary or description of what the skill/topic is."
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of concrete steps, rules, or key facts related to the skill."
                    }
                },
                "required": ["skill_name", "description", "steps"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_skills",
            "description": "Search your persistent skill memory for previously learned skills or topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic or keyword to search for."
                    }
                },
                "required": ["query"]
            }
        }
    },
    # --- Phase 4 — Agentic Autonomy Tools ---
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "Execute Python or Bash code safely in an isolated sandbox with resource limits (30s timeout, 256MB memory). Use this to run code snippets, test solutions, do calculations, or process data. Returns stdout, stderr, and execution time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The source code to execute."
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language: 'python' or 'bash'. Defaults to 'python'."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_operation",
            "description": "Perform git operations on a repository. Supports: status, diff, log, branch (list/create/switch), commit (with auto-generated messages), and stash (push/pop/list). Use this when the user asks about git, version control, or code changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The git operation: 'status', 'diff', 'log', 'branch', 'commit', or 'stash'."
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the git repository. Defaults to current directory."
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message (for 'commit' operation). Auto-generated if not provided."
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "Branch name (for 'branch' operation with create/switch action)."
                    },
                    "action": {
                        "type": "string",
                        "description": "Sub-action for branch ('list'/'create'/'switch') or stash ('push'/'pop'/'list')."
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of commits to show (for 'log' operation, default 10)."
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged diff instead of unstaged (for 'diff' operation)."
                    }
                },
                "required": ["operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "research_topic",
            "description": "Conduct thorough autonomous research on any topic. Searches the web, reads multiple articles, synthesizes a structured report, and saves it as a markdown file. Use this when the user asks you to research, investigate, or write a report on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic or question to research."
                    },
                    "depth": {
                        "type": "string",
                        "description": "Research depth: 'quick' (3 sources), 'standard' (5 sources), or 'deep' (8 sources). Default: 'standard'."
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Automatically plan and execute a complex, multi-step goal using the LangGraph orchestrator. The agent will decompose the goal, run the steps sequentially, and dynamically backtrack or replan if any step fails. Use this for complex system setups or workflows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "The goal to plan for, in natural language."
                    }
                },
                "required": ["goal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_background_task",
            "description": "Submit a long-running task to the background queue. The task runs asynchronously and you will be notified when it completes. Use this for tasks that take more than a few seconds (e.g., deep research, large file processing, code analysis). Supported task types: 'research' (params: topic, depth), 'code_exec' (params: code, language).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "A human-readable name for the task."
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Type of task: 'research' or 'code_exec'."
                    },
                    "params": {
                        "type": "string",
                        "description": "JSON string of parameters for the task. For research: {\"topic\": \"...\", \"depth\": \"standard\"}. For code_exec: {\"code\": \"...\", \"language\": \"python\"}."
                    }
                },
                "required": ["name", "task_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code",
            "description": "Analyze a local code file (DeepCode integration). Reads the file and prepares it for LLM review to find bugs, security issues, or suggest improvements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the code file."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": "Transcribe an audio file to text (Otter.ai integration via Whisper).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the audio file."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cloud_sync",
            "description": "Sync files with cloud storage (Google Drive, Dropbox, OneDrive). Use to upload files or list cloud storage contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "'upload' or 'list'."
                    },
                    "target": {
                        "type": "string",
                        "description": "The local file/folder path to upload (only needed if action is 'upload')."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_time",
            "description": "Track time spent on tasks (Tricount/Time integration).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": "Name of the task."
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration to log in minutes."
                    }
                },
                "required": ["task_name", "duration_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_data",
            "description": "Initialize a data visualization engine for a dataset (Tableau/Power BI integration). Instructs the LLM on how to generate the corresponding code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_info": {
                        "type": "string",
                        "description": "Description or path to the dataset you want to visualize."
                    }
                },
                "required": ["dataset_info"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deep_think",
            "description": "Trigger a Tree-of-Thoughts (ToT) reasoning process for complex logic, math, or abstract problems. It will internally generate multiple logical paths, score them, and return the best step-by-step conclusion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {
                        "type": "string",
                        "description": "The complex problem or question to reason about."
                    }
                },
                "required": ["problem"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_outcome",
            "description": "Run an objective causal simulation sandbox to predict 'what if' scenarios based on logical, physical, and historical rules. Returns initial state, primary effect, cascading effects, and final outcome.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "description": "The hypothetical scenario or action to simulate."
                    },
                    "context": {
                        "type": "string",
                        "description": "Any necessary background context or rules."
                    }
                },
                "required": ["scenario"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_physics",
            "description": "Run a 3D headless physics simulation (PyBullet) to test physical outcomes in a virtual sandbox before taking action. Supported scenarios: 'drop_test'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "description": "The physical scenario to simulate (e.g., 'drop_test')."
                    }
                },
                "required": ["scenario"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "drone_action",
            "description": "Control an aerial drone using MAVLink telemetry. Allows connecting, taking off, and landing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'connect', 'takeoff', or 'land'."
                    },
                    "connection_string": {
                        "type": "string",
                        "description": "The connection string (for 'connect' action), e.g. 'tcp:127.0.0.1:5760'."
                    },
                    "altitude": {
                        "type": "number",
                        "description": "Altitude in meters (for 'takeoff' action)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_swarm_task",
            "description": "Dispatch a specialized task to the Multi-Agent Swarm for parallel reasoning. The swarm includes a CodeAgent and a SafetyAgent. Returns the swarm's synthesized response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "The type of task: 'code' (for code review/debugging) or 'safety_check' (to evaluate action safety)."
                    },
                    "payload_json": {
                        "type": "string",
                        "description": "A JSON string containing the payload (e.g., {\"code\": \"def foo():...\", \"task\": \"Review this\"} or {\"content\": \"command to run\"})."
                    }
                },
                "required": ["task_type", "payload_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_snapshot",
            "description": "Create a secure backup snapshot of ALAS's entire memory state (SQLite + Knowledge Graph). Use this before risky operations or at the user's request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for the snapshot (e.g., 'pre-risky-operation', 'manual')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "heal_memory",
            "description": "Run an integrity check on ALAS's core SQLite database. Use this if ALAS seems confused or reports database corruption.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_dream",
            "description": "Initiate a dream consolidation cycle. ALAS will enter a deep reflective state to process recent episodic memories and extract profound insights to store in its long-term Knowledge Graph. Use this during idle periods or when asked to reflect.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "self_improve",
            "description": "Trigger the Automated LoRA Training Pipeline. ALAS will extract the highest-rated historical interactions and train a Parameter-Efficient Fine-Tuning adapter on its own neural weights to permanently improve its behavior.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def get_all_tools():
    """Get all available tools, including built-in, plugin, and MCP tools."""
    from backend.app.plugins.base import get_plugin_manager
    from backend.app.mcp.mcp_manager import get_mcp_manager
    
    legacy_tools = {"read_local_file", "write_local_file", "list_directory", "query_database", "manage_files", "git_operation"}
    tools = [t for t in AVAILABLE_TOOLS if t["function"]["name"] not in legacy_tools]
    
    # Inject plugin tools
    try:
        plugin_tools = get_plugin_manager().get_all_tools()
        tools.extend(plugin_tools)
    except Exception as e:
        logger.error(f"Failed to load plugin tools: {e}")
        
    # Inject MCP tools
    try:
        mcp_tools = get_mcp_manager().get_all_tool_schemas()
        tools.extend(mcp_tools)
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}")
        
    return tools

async def execute_tool(tool_call) -> Dict[str, Any]:
    """
    Execute a tool requested by the LLM and return the result formatted for Ollama.
    """
    # Handle different Ollama python client object structures
    name = getattr(tool_call.function, "name", "")
    
    if not name:
        return {"role": "tool", "content": "Error: Tool name not provided."}

    logger.info(f"🛠️ LLM requested tool execution: {name}")
    
    # Extract arguments safely
    try:
        # Some versions of ollama client return a dict, some return a Pydantic object
        args = getattr(tool_call.function, "arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
    except Exception as e:
        logger.error(f"Failed to parse tool arguments for {name}: {e}")
        args = {}

    try:
        if name in TOOL_FUNCTIONS:
            func = TOOL_FUNCTIONS[name]
            result_content = func(**args)
        else:
            # Check plugins
            from backend.app.plugins.base import get_plugin_manager
            from backend.app.mcp.mcp_manager import get_mcp_manager
            try:
                result_content = get_plugin_manager().execute_tool(name, args)
            except ValueError:
                # If not a plugin, check MCP servers
                try:
                    mcp_manager = get_mcp_manager()
                    mcp_schemas = mcp_manager.get_all_tool_schemas()
                    if any(t["function"]["name"] == name for t in mcp_schemas):
                        mcp_result = await mcp_manager.call_tool(name, args)
                        result_content = mcp_result.get("content", "Error executing MCP tool.")
                    else:
                        result_content = f"Error: Unknown tool '{name}'."
                        logger.warning(f"Unknown tool requested: {name}")
                except Exception as mcp_err:
                    result_content = f"Error executing MCP tool '{name}': {mcp_err}"
                    logger.error(result_content)
                
        # Ensure result is a string
        if not isinstance(result_content, str):
            result_content = str(result_content)
            
        return {"role": "tool", "content": result_content}
        
    except Exception as e:
        logger.error(f"Error executing tool '{name}': {e}")
        return {
            "role": "tool",
            "content": f"Error executing tool: {str(e)}"
        }
