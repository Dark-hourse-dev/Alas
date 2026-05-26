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


def execute_shell(command: str) -> str:
    """Execute a shell command and return its output."""
    try:
        logger.warning(f"Executing shell command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        
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
            
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing shell command: {e}"


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


# --- Tool Registry Mapping ---
# Maps the tool name (from LLM) to the actual Python function
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "calculate": calculate,
    "read_local_file": read_local_file,
    "write_local_file": write_local_file,
    "list_directory": list_directory,
    "execute_shell": execute_shell,
    "search_web": search_web,
    "read_webpage": read_webpage,
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
            "description": "Execute a shell command (Bash/Terminal) on the host system. Use this to install packages, run scripts, manage git, etc.",
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
    }
]

def execute_tool(tool_call) -> Dict[str, Any]:
    """
    Execute a tool requested by the LLM and return the result formatted for Ollama.
    """
    # Handle different Ollama python client object structures
    name = getattr(tool_call.function, "name", "")
    
    if not name:
        return {"role": "tool", "content": "Error: Tool name not provided."}

    logger.info(f"🛠️ LLM requested tool execution: {name}")
    
    if name not in TOOL_FUNCTIONS:
        logger.warning(f"Unknown tool requested: {name}")
        return {"role": "tool", "content": f"Error: Unknown tool '{name}'."}
        
    func = TOOL_FUNCTIONS[name]
    
    # Extract arguments safely
    try:
        # Some versions of ollama client return a dict, some return a Pydantic object
        args = getattr(tool_call.function, "arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
    except Exception as e:
        logger.error(f"Failed to parse tool arguments: {e}")
        args = {}

    try:
        # Execute the Python function with the provided arguments
        result_content = func(**args)
        logger.info(f"🛠️ Tool '{name}' executed successfully.")
        
        return {
            "role": "tool",
            "content": str(result_content)
        }
    except Exception as e:
        logger.error(f"Error executing tool '{name}': {e}")
        return {
            "role": "tool",
            "content": f"Error executing tool: {str(e)}"
        }
