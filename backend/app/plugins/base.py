"""
ALAS Plugin System — Base classes and registry.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("alas.plugins")

class ALASPlugin:
    """Base class for all ALAS plugins."""
    
    name = "base_plugin"
    description = "Base plugin description"
    version = "1.0.0"
    author = "ALAS"
    
    def __init__(self):
        self.enabled = True
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return a list of tool definitions (OpenAI function calling format) for the LLM."""
        return []
        
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool provided by this plugin."""
        raise NotImplementedError(f"Plugin {self.name} does not implement tool execution.")
        
    def on_load(self):
        """Called when the plugin is loaded."""
        pass
        
    def on_unload(self):
        """Called when the plugin is unloaded."""
        pass

class PluginManager:
    """Manages loading, unloading, and executing plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, ALASPlugin] = {}
        
    def register(self, plugin: ALASPlugin):
        """Register a plugin."""
        if plugin.name in self._plugins:
            logger.warning(f"Plugin {plugin.name} is already registered. Overwriting.")
        self._plugins[plugin.name] = plugin
        plugin.on_load()
        logger.info(f"🔌 Plugin loaded: {plugin.name} v{plugin.version}")
        
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get tools from all enabled plugins."""
        tools = []
        for plugin in self._plugins.values():
            if plugin.enabled:
                tools.extend(plugin.get_tools())
        return tools
        
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Find the plugin that provides the tool and execute it."""
        for plugin in self._plugins.values():
            if plugin.enabled:
                # We check if the tool is in this plugin's provided tools
                tool_names = [t["function"]["name"] for t in plugin.get_tools()]
                if name in tool_names:
                    return plugin.execute_tool(name, arguments)
        raise ValueError(f"Tool {name} not found in any loaded plugin.")
        
    def list_plugins(self) -> List[Dict[str, Any]]:
        """Get info about all registered plugins."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "author": p.author,
                "enabled": p.enabled
            }
            for p in self._plugins.values()
        ]

# Singleton
_plugin_manager = None

def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
