import asyncio
import logging
import threading
from typing import Any, Dict, List, Tuple

from tron_ai.modules.mcp.utils import EventLoopManager, ConnectionPool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Manages registration and lookup of MCP tools.
    Maps server tools to local function proxies.
    """

    def __init__(
        self, event_loop_manager: EventLoopManager, connection_pool: ConnectionPool
    ):
        self._event_loop = event_loop_manager
        self._connection_pool = connection_pool
        self._tools = {}  # full_name -> (server_name, tool_name, tool_info)
        self._tools_lock = threading.Lock()

    async def discover_tools(self, server_name: str) -> List[Tuple[str, str, Any]]:
        """
        Discover tools available on a server.

        Args:
            server_name: Name of the server to query

        Returns:
            List of (full_name, server_name, tool_name, tool_info) tuples
        """
        discovered_tools = []

        # Get connection
        connection = self._connection_pool.get_connection(server_name)
        if not connection:
            logger.error(f"Cannot discover tools for {server_name}: No connection")
            return discovered_tools

        try:
            # List available tools
            response = await connection.list_tools()

            # Extract tools from response
            mcp_tools = []
            if hasattr(response, "tools"):
                mcp_tools = response.tools
            elif isinstance(response, list):
                mcp_tools = response
            else:
                try:
                    mcp_tools = list(response)
                except Exception:
                    logger.error(f"Cannot convert tools response to list: {response}")

            # Process each tool
            for tool in mcp_tools:
                try:
                    # Extract tool info
                    if hasattr(tool, "name") and hasattr(tool, "description"):
                        tool_name = tool.name
                        tool_info = tool
                    elif (
                        isinstance(tool, dict)
                        and "name" in tool
                        and "description" in tool
                    ):
                        tool_name = tool["name"]
                        tool["description"]  # noqa: F401
                        tool_info = tool
                    elif isinstance(tool, tuple) and len(tool) >= 2:
                        tool_name = tool[0]
                        tool[1]  # noqa: F401
                        tool_info = tool
                    else:
                        logger.warning(f"Unknown tool format: {type(tool)}, {tool}")
                        continue

                    # Create full name
                    full_name = f"{server_name}_{tool_name}"

                    # Add to discovered tools
                    discovered_tools.append(
                        (full_name, server_name, tool_name, tool_info)
                    )

                except Exception as e:
                    logger.error(f"Error processing tool {tool}: {str(e)}")

            return discovered_tools

        except Exception as e:
            logger.error(f"Error discovering tools for {server_name}: {str(e)}")
            return discovered_tools

    def register_tools(self, discovered_tools: List[Tuple[str, str, str, Any]]):
        """Register discovered tools"""
        with self._tools_lock:
            for full_name, server_name, tool_name, tool_info in discovered_tools:
                self._tools[full_name] = (server_name, tool_name, tool_info)

    def create_tool_proxy(self, full_name: str, server_name: str, tool_name: str):
        """
        Create a proxy function for a tool.

        Args:
            full_name: Full name of the tool (server_name_tool_name)
            server_name: Name of the server hosting the tool
            tool_name: Name of the tool on the server

        Returns:
            Function that proxies calls to the tool
        """
        # Get tool info if available
        tool_info = None
        with self._tools_lock:
            if full_name in self._tools:
                _, _, tool_info = self._tools[full_name]

        # Get tool description
        tool_description = "No description available"
        if tool_info:
            if hasattr(tool_info, "description"):
                tool_description = tool_info.description
            elif isinstance(tool_info, dict) and "description" in tool_info:
                tool_description = tool_info["description"]
            elif isinstance(tool_info, tuple) and len(tool_info) >= 2:
                tool_description = tool_info[1]

        # Create the proxy function
        def tool_proxy(**kwargs):
            """Proxy function that forwards calls to the MCP server"""

            # Create async function for call
            async def call_tool():
                # Get connection
                connection = self._connection_pool.get_connection(server_name)
                if not connection:
                    raise ValueError(
                        f"Cannot call tool {full_name}: No connection to {server_name}"
                    )

                # Call the tool
                max_retries = 3
                retry_count = 0
                last_error = None

                while retry_count < max_retries:
                    try:
                        # Call the tool on the MCP server
                        result = await connection.call_tool(tool_name, arguments=kwargs)

                        # Process the result
                        if hasattr(result, "result"):
                            return result.result
                        elif isinstance(result, dict) and "result" in result:
                            return result["result"]
                        else:
                            return result

                    except Exception as e:
                        last_error = e
                        retry_count += 1
                        logger.warning(
                            f"Error calling tool {full_name} (attempt {retry_count}/{max_retries}): {str(e)}"
                        )

                        if retry_count < max_retries:
                            # Wait with exponential backoff
                            await asyncio.sleep(0.5 * (2**retry_count))

                            # Try to get a fresh connection
                            try:
                                # Get a fresh connection for the retry
                                connection = self._connection_pool.get_connection(
                                    server_name
                                )
                                if not connection:
                                    raise ValueError(
                                        f"Cannot reconnect to {server_name}"
                                    )
                            except Exception as reconnect_error:
                                logger.error(
                                    f"Error reconnecting to {server_name}: {str(reconnect_error)}"
                                )
                                # Continue with existing connection or fail

                # If we get here, all retries failed
                raise ValueError(
                    f"Failed to call tool {full_name} after {max_retries} attempts: {str(last_error)}"
                )

            # Submit async function to event loop and wait for result
            try:
                return self._event_loop.run_sync(call_tool)
            except Exception as e:
                raise ValueError(f"Error calling tool {full_name}: {str(e)}")

        # Set function metadata
        tool_proxy.__name__ = full_name
        tool_proxy.__doc__ = tool_description

        return tool_proxy

    def get_all_proxies(self) -> Dict[str, Any]:
        """Get proxy functions for all registered tools"""
        proxies = {}

        with self._tools_lock:
            for full_name, (server_name, tool_name, _) in self._tools.items():
                proxies[full_name] = self.create_tool_proxy(
                    full_name, server_name, tool_name
                )

        return proxies

    def discover_and_register_all_tools(self, force_refresh=False):
        """Discover and register tools from all servers"""
        all_discovered_tools = []

        # Get all server names
        server_names = self._connection_pool.get_all_server_names()

        # Clear existing tools if force refresh is requested
        if force_refresh:
            with self._tools_lock:
                self._tools = {}
                logger.info("Cleared existing tools for refresh")

        # Discover tools from each server
        for server_name in server_names:
            try:
                # Discover tools in the event loop
                discovered_tools = self._event_loop.run_sync(
                    lambda: self.discover_tools(server_name)
                )

                if discovered_tools:
                    all_discovered_tools.extend(discovered_tools)
                    logger.info(
                        f"Discovered {len(discovered_tools)} tools from {server_name}"
                    )
                else:
                    logger.warning(f"No tools discovered from {server_name}")

            except Exception as e:
                logger.error(f"Error discovering tools from {server_name}: {str(e)}")

        # Register all discovered tools
        self.register_tools(all_discovered_tools)

        return all_discovered_tools
