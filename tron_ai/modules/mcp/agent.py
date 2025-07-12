"""
MCPAgent - Master Control Program Agent

This agent is responsible for coordinating with multiple MCP (Master Control Program) servers
that are defined in the mcp_servers.json configuration file.

The MCPAgent uses MultiMCPClient and MCPQueue to:
- Connect to multiple MCP servers
- Call functions across these servers
- Manage distributed processing tasks
- Coordinate system-wide operations
"""

import asyncio
import logging
from typing import Optional, Any, Callable
from functools import wraps
import traceback

# Third-party imports
from adalflow.core.func_tool import FunctionTool
from adalflow.core.tool_manager import ToolManager
from pydantic import Field

# Local imports
from tron_ai.models.agent import Agent as TronAgent
from tron_ai.models.prompts import Prompt
from tron_ai.modules.mcp.client import Client

# Configure logging
# logging.basicConfig(level=logging.INFO) # Removed: Handled by central config
logger = logging.getLogger("mcp_agent")


def wrap_async_function(async_fn: Callable) -> Callable:
    """Wrap an async function to run in the event loop."""

    @wraps(async_fn)
    def wrapper(*args, **kwargs) -> Any:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(async_fn(*args, **kwargs))

    return wrapper


class Agent(TronAgent):
    """Agent for a single MCP server."""
    server_name: str = Field()
    server_config: dict = Field()
    mcp_client: Optional[Client] = None

    def __init__(self, server_name: str, server_config: dict, **kwargs):
        super().__init__(
            name=f"MCP Agent ({server_name})",
            description=f"Coordinates with MCP server '{server_name}' for distributed task execution",
            prompt=Prompt(
                text=f"""You are a Master Control Program (MCP) expert for server '{server_name}'.\n\nYour responsibilities include:\n- Distributed Task Coordination\n- Server Management\n- Tool Management\n- Error Handling\n\nAlways follow best practices for reliability and performance."""
            ),
            tool_manager=None,
            server_name=server_name,
            server_config=server_config,
            **kwargs
        )

    async def initialize(self):
        try:
            logger.info(f"Initializing MCPAgent for server {self.server_name}...")
            # Prepare the config for a single server
            server_type = self.server_config.get("type", "stdio")
            connection_params = self.server_config.copy()
            connection_params.pop("type", None)
            self.mcp_client = await Client.create([
                {
                    "name": self.server_name,
                    "type": server_type,
                    "connection_params": connection_params,
                }
            ])
            functions = await self.mcp_client.list_functions()
            if not functions:
                logger.warning(f"No functions available on MCP server {self.server_name}")
            else:
                logger.info(f"Connected to MCP server {self.server_name} with {len(functions.get(self.server_name, []))} functions")
            await self._generate_tools_from_functions()
        except Exception as e:
            logger.error(f"Error during MCPAgent initialization: {str(e)}")
            if self.mcp_client:
                await self.cleanup()
            raise

    async def cleanup(self):
        """Clean up resources and close connections."""
        if self.mcp_client:
            try:
                await self.mcp_client.disconnect()
            except (RuntimeError, asyncio.CancelledError) as e:
                if (
                    "cancel scope" in str(e)
                    or "Event loop is closed" in str(e)
                    or isinstance(e, asyncio.CancelledError)
                ):
                    logger.warning(f"Suppressed shutdown error: {e}")
                else:
                    raise
            self.mcp_client = None
            logger.info("MultiMCPClient disconnected")
        logger.info("MCPAgent cleanup complete")

    @classmethod
    async def cleanup_all(cls):
        """Class method to clean up all resources."""
        logger.info("Cleaning up all MCPAgent resources")
        # Nothing to do at class level since we moved to instance-based management
        logger.info("MCPAgent cleanup complete")

    async def _generate_tools_from_functions(self):
        """Generate tools dynamically from available MCP server functions."""
        if not self.mcp_client:
            logger.error("Cannot generate tools: MCP client not initialized")
            return

        try:
            logger.info(f"[{self.server_name}] Starting tool generation")
            functions_by_server = await self.mcp_client.list_functions()
            logger.info(f"[{self.server_name}] Functions by server: {list(functions_by_server.keys())}")
            
            tools = []
            function_names = set()
            for server_name, functions in functions_by_server.items():
                logger.info(f"[{self.server_name}] Processing server '{server_name}' with {len(functions)} functions")
                if server_name != self.server_name:
                    logger.info(f"[{self.server_name}] Skipping server '{server_name}' (not our server)")
                    continue
                    
                logger.info(f"[{self.server_name}] Found {len(functions)} functions for our server")
                for i, func_info in enumerate(functions):
                    func_name = func_info["name"]
                    logger.debug(f"[{self.server_name}] Processing function {i+1}/{len(functions)}: {func_name}")
                    func_description = func_info["description"]
                    func_schema = func_info.get("schema", {})
                    tool_name = func_name
                    if func_name in function_names:
                        tool_name = f"{self.server_name.replace('-', '_')}_{func_name}"
                    else:
                        function_names.add(func_name)
                    param_info = ""
                    if func_schema:
                        properties = func_schema.get("properties", {})
                        required = func_schema.get("required", [])
                        if properties:
                            param_info = "\nParameters:\n"
                            for name, details in properties.items():
                                req = "(Required)" if name in required else "(Optional)"
                                default = (
                                    f", default: {details.get('default')}"
                                    if "default" in details
                                    else ""
                                )
                                desc = details.get("description", "")
                                if desc and "." in desc:
                                    desc = desc.split(".")[0] + "."
                                param_info += f"- {name}: {desc} {req}{default}\n"
                                
                    async def execute_server_function(
                        function_name=func_name,
                        *args,
                        **kwargs,
                    ):                        
                        try:
                            if not self.mcp_client:
                                return "MCPAgent not initialized"
                            
                            # Remove priority from kwargs if present
                            kwargs.pop("priority", None)
                            
                            # Call function directly on MCP client
                            request = await self.mcp_client.call_function(
                                server_name=self.server_name,
                                function_name=function_name,
                                arguments=kwargs
                            )
                            
                            # Process result
                            if hasattr(request, "result"):
                                return request.result
                            
                            if hasattr(request, "content"):
                                return request.content[0].text
                        
                            return f"Function executed successfully: {request}"
                            
                        except Exception as e:
                            logger.error(f"Error executing function {function_name}: {str(e)}")
                            return f"Error executing function: {str(e)}"
                        
                    def create_tool_function(
                        function_name,
                        tool_name,
                        func_description,
                        param_info,
                    ):
                        async def tool_function(*args, **kwargs):
                            # Always propagate session_id if present
                            session_id = kwargs.get("session_id")
                            # If this tool is calling execute_on_swarm, enforce session_id propagation
                            if "execute_on_swarm" in func_name or "agent" in func_name:
                                if not session_id:
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.warning(f"[SESSION] MCP tool '{tool_name}' called without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                                    assert False, f"MCP tool '{tool_name}' called without session_id. Session tracking will break."
                            kwargs.pop("server_name", None)
                            return await execute_server_function(
                                function_name=function_name,
                                *args,
                                **kwargs,
                            )
                        tool_function.__name__ = tool_name
                        tool_function.__doc__ = f"{func_description}\n\nServer: {self.server_name}\nFunction: {function_name}{param_info}"
                        return tool_function
                    tool_function = create_tool_function(
                        func_name, tool_name, func_description, param_info
                    )
                    tool = FunctionTool(fn=wrap_async_function(tool_function))
                    tools.append(tool)
                    logger.debug(f"[{self.server_name}] Created tool '{tool_name}' for function '{func_name}'")
            
            self.tool_manager = ToolManager(tools=tools)
            logger.info(f"[{self.server_name}] Generated {len(tools)} tools from MCP server functions")
            logger.info(f"[{self.server_name}] Tool names: {[tool.fn.__name__ for tool in tools]}")
        except Exception as e:
            logger.error(f"[{self.server_name}] Error generating tools from functions: {str(e)}")
            raise
