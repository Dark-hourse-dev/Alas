"""
ALAS MCP (Model Context Protocol) Module.
Manages connections to standard MCP servers and provides a unified tool interface.
"""

from .mcp_manager import MCPManager, get_mcp_manager

__all__ = ["MCPManager", "get_mcp_manager"]
