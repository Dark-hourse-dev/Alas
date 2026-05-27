"""
ALAS Default Plugins — Built-in tools for Phase 4.
"""

from backend.app.plugins.base import ALASPlugin, get_plugin_manager
import logging

logger = logging.getLogger("alas.plugins.defaults")

class SystemStatsPlugin(ALASPlugin):
    name = "system_stats"
    description = "Provides detailed system statistics."
    version = "1.0.0"
    
    def get_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_advanced_sysinfo",
                    "description": "Get advanced system information like load average and swap usage.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        
    def execute_tool(self, name, arguments):
        if name == "get_advanced_sysinfo":
            import psutil
            import os
            
            swap = psutil.swap_memory()
            load = os.getloadavg() if hasattr(os, "getloadavg") else ("N/A", "N/A", "N/A")
            
            return (
                f"Advanced System Stats:\n"
                f"- Load Average: {load}\n"
                f"- Swap Usage: {swap.percent}%\n"
                f"- Context Switches: {psutil.cpu_stats().ctx_switches}"
            )
        raise ValueError(f"Unknown tool {name}")

def register_default_plugins():
    manager = get_plugin_manager()
    manager.register(SystemStatsPlugin())
    logger.info("Default plugins registered.")
