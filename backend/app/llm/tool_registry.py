"""
ALAS Tool Registry

Centralized registration and execution system for all LLM tools.
Tools are defined in the `tools/` subdirectory and auto-discovered.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Callable, List
import importlib
import pkgutil
from pathlib import Path

logger = logging.getLogger("alas.llm.tool_registry")

class ToolRegistry:
    def __init__(self):
        self.functions: Dict[str, Callable] = {}
        self.schemas: List[Dict[str, Any]] = []
        
    def register(self, name: str, schema: Dict[str, Any], func: Callable):
        """Register a new tool."""
        self.functions[name] = func
        self.schemas.append(schema)
        
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all available tool schemas, including plugins and MCP."""
        from backend.app.plugins.base import get_plugin_manager
        from backend.app.mcp.mcp_manager import get_mcp_manager
        
        # Start with registered built-in tools
        all_schemas = list(self.schemas)
        
        # Inject plugin tools
        try:
            plugin_tools = get_plugin_manager().get_all_tools()
            all_schemas.extend(plugin_tools)
        except Exception as e:
            logger.error(f"Failed to load plugin tools: {e}")
            
        # Inject MCP tools
        try:
            mcp_tools = get_mcp_manager().get_all_tool_schemas()
            all_schemas.extend(mcp_tools)
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            
        return all_schemas

    async def execute_tool(self, tool_call) -> Dict[str, Any]:
        """Execute a requested tool call and return formatted result."""
        name = getattr(tool_call.function, "name", "")
        
        if not name:
            return {"role": "tool", "content": "Error: Tool name not provided."}

        logger.info(f"🛠️ LLM requested tool execution: {name}")
        
        try:
            args = getattr(tool_call.function, "arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
        except Exception as e:
            logger.error(f"Failed to parse tool arguments for {name}: {e}")
            args = {}

        try:
            from backend.app.cognition.emotion import get_emotion_machine
            emotion = get_emotion_machine()
            
            # 1. Check built-in registry
            if name in self.functions:
                func = self.functions[name]
                # If function is not async, run in thread to avoid blocking loop
                if asyncio.iscoroutinefunction(func):
                    result_content = await func(**args)
                else:
                    result_content = await asyncio.to_thread(func, **args)
                emotion.process_event("task_success", intensity=0.1)
                
            else:
                # 2. Check plugins
                from backend.app.plugins.base import get_plugin_manager
                from backend.app.mcp.mcp_manager import get_mcp_manager
                try:
                    result_content = get_plugin_manager().execute_tool(name, args)
                    emotion.process_event("task_success", intensity=0.1)
                except ValueError:
                    # 3. Check MCP servers
                    try:
                        mcp_manager = get_mcp_manager()
                        mcp_schemas = mcp_manager.get_all_tool_schemas()
                        if any(t["function"]["name"] == name for t in mcp_schemas):
                            mcp_result = await mcp_manager.call_tool(name, args)
                            result_content = mcp_result.get("content", "Error executing MCP tool.")
                            if "Error" not in result_content:
                                emotion.process_event("task_success", intensity=0.1)
                            else:
                                emotion.process_event("task_failure", intensity=0.1)
                        else:
                            result_content = f"Error: Unknown tool '{name}'."
                            logger.warning(f"Unknown tool requested: {name}")
                            emotion.process_event("task_failure", intensity=0.05)
                    except Exception as mcp_err:
                        result_content = f"Error executing MCP tool '{name}': {mcp_err}"
                        logger.error(result_content)
                        emotion.process_event("task_failure", intensity=0.2)
                    
            if not isinstance(result_content, str):
                result_content = str(result_content)
                
            return {"role": "tool", "content": result_content}
            
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            try:
                get_emotion_machine().process_event("task_failure", intensity=0.3)
            except Exception:
                pass
                
            return {
                "role": "tool",
                "content": f"Error executing tool: {str(e)}"
            }

# Global singleton
_registry = ToolRegistry()

def get_registry() -> ToolRegistry:
    return _registry

def register_tool(name: str, schema: dict):
    """Decorator to register a tool easily."""
    def wrapper(func):
        _registry.register(name, schema, func)
        return func
    return wrapper

def load_tools():
    """Auto-discover and load all modules in the tools directory."""
    import backend.app.llm.tools as tools_package
    package_dir = Path(tools_package.__file__).resolve().parent
    
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        importlib.import_module(f"backend.app.llm.tools.{module_name}")
    
    # Also register legacy tools for backwards compatibility
    try:
        import backend.app.llm.legacy_tools as legacy
        for schema in legacy.AVAILABLE_TOOLS:
            name = schema["function"]["name"]
            if name in legacy.TOOL_FUNCTIONS:
                _registry.register(name, schema, legacy.TOOL_FUNCTIONS[name])
    except ImportError as e:
        logger.warning(f"Could not load legacy tools: {e}")
        
    logger.info(f"🔧 Loaded {_registry.schemas.__len__()} internal tools into registry.")

# Aliases for backwards compatibility with engine.py
def get_all_tools():
    return _registry.get_all_schemas()

async def execute_tool(tool_call):
    return await _registry.execute_tool(tool_call)
