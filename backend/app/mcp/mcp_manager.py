import asyncio
import logging
from typing import Dict, Any, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("alas.mcp.manager")

class MCPManager:
    """
    Manages connections to standard Model Context Protocol (MCP) servers.
    Provides a unified interface to list and execute tools across all connected servers.
    """
    def __init__(self):
        self._servers: Dict[str, dict] = {}  # server_name -> {"session": ClientSession, "stdio": context_manager}
        self._tools_cache: Dict[str, dict] = {} # tool_name -> {"server_name": "...", "schema": {...}}

    async def connect_stdio_server(self, server_name: str, command: str, args: List[str]):
        """Connect to an MCP server running as a local subprocess."""
        if server_name in self._servers:
            logger.warning(f"MCP Server '{server_name}' is already connected.")
            return

        logger.info(f"Connecting to MCP Server '{server_name}' via stdio ({command} {' '.join(args)})")
        
        server_parameters = StdioServerParameters(
            command=command,
            args=args,
            env=None
        )

        # Launch the connection in a background task
        task = asyncio.create_task(self._run_server_loop(server_name, server_parameters))
        
        self._servers[server_name] = {
            "task": task,
            "session": None # Will be set by the background task
        }

    async def _run_server_loop(self, server_name: str, server_parameters: StdioServerParameters):
        try:
            async with stdio_client(server_parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    self._servers[server_name]["session"] = session
                    
                    logger.info(f"Successfully connected to MCP Server '{server_name}'.")
                    await self._refresh_tools_for_server(server_name)
                    
                    # Keep the context alive
                    while True:
                        await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info(f"MCP Server '{server_name}' loop cancelled.")
        except Exception as e:
            logger.error(f"MCP Server '{server_name}' connection died: {e}")
            if server_name in self._servers:
                self._servers[server_name]["session"] = None

    async def _refresh_tools_for_server(self, server_name: str):
        """Fetch tools from the server and cache them in Ollama schema format."""
        session = self._servers.get(server_name, {}).get("session")
        if not session:
            return
            
        try:
            tools_response = await session.list_tools()
            
            # Remove old tools from this server
            self._tools_cache = {name: info for name, info in self._tools_cache.items() if info["server_name"] != server_name}
            
            for tool in tools_response.tools:
                # Convert MCP tool schema to Ollama tool schema format
                ollama_schema = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or f"Executes {tool.name}",
                        "parameters": tool.inputSchema
                    }
                }
                self._tools_cache[tool.name] = {
                    "server_name": server_name,
                    "schema": ollama_schema
                }
            logger.info(f"Loaded {len(tools_response.tools)} tools from MCP Server '{server_name}'.")
        except Exception as e:
            logger.error(f"Failed to list tools from MCP Server '{server_name}': {e}")

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return all tools formatted for the Ollama chat endpoint."""
        return [info["schema"] for info in self._tools_cache.values()]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the appropriate MCP server."""
        if tool_name not in self._tools_cache:
            return {"role": "tool", "content": f"Error: Tool '{tool_name}' not found in any MCP server."}
        
        server_name = self._tools_cache[tool_name]["server_name"]
        session = self._servers.get(server_name, {}).get("session")
        if not session:
             return {"role": "tool", "content": f"Error: MCP Server '{server_name}' is not running."}
        
        try:
            logger.info(f"Executing MCP tool '{tool_name}' on server '{server_name}'...")
            result = await session.call_tool(tool_name, arguments)
            
            # Format output (MCP tools return an array of text/image content blocks)
            text_outputs = []
            for content in result.content:
                if content.type == "text":
                    text_outputs.append(content.text)
                else:
                    text_outputs.append(f"[{content.type} output]")
                    
            final_output = "\\n".join(text_outputs)
            return {"role": "tool", "content": final_output}
            
        except Exception as e:
            logger.error(f"MCP Tool execution failed: {e}")
            return {"role": "tool", "content": f"Error executing '{tool_name}': {str(e)}"}

    async def shutdown(self):
        """Close all MCP connections gracefully."""
        for name, data in self._servers.items():
            if "task" in data:
                data["task"].cancel()
        self._servers.clear()
        self._tools_cache.clear()

# Global instance
_mcp_manager: Optional[MCPManager] = None

def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
