import logging
import asyncio
import os
from typing import Dict, List, Optional, Any
from contextlib import AsyncExitStack
import traceback

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from tron_intelligence.utils import json as json


class Client:
    """
    A client that can connect to multiple MCP servers simultaneously.

    This client initializes connections to multiple MCP servers during instantiation
    and provides methods to list functions across servers and call functions on specific servers.
    """

    def __init__(self, log_level=logging.INFO):
        """
        Initialize the MultiMCPClient.

        Args:
            log_level: Logging level (default: logging.INFO)
        """
        # Set up logger
        self.logger = logging.getLogger("tron_intelligence.modules.mcp.multi_mcp_client")
        self.logger.setLevel(log_level)

        self.logger.info("Initializing MultiMCPClient")

        self._exit_stack = AsyncExitStack()
        self._sessions_by_name: Dict[str, ClientSession] = {}

    @classmethod
    async def create(cls, server_configs: List[Dict[str, Any]], log_level=logging.INFO):
        """
        Create and initialize a MultiMCPClient with server connections.

        Args:
            server_configs: List of server configuration dictionaries with:
                - name: server name (str)
                - type: 'stdio' or 'sse' (str)
                - connection_params: dict with connection parameters
                  (e.g., {command: str, args: List[str], env: Dict[str, str]} for stdio;
                   {url: str} for sse)
            log_level: Logging level (default: logging.INFO)

        Returns:
            Initialized MultiMCPClient instance
        """
        client = cls(log_level=log_level)
        await client._initialize_servers(server_configs)
        client.logger.info(
            f"Initialized {len(client._sessions_by_name)} MCP server connections"
        )
        return client

    @classmethod
    async def from_config_file(
        cls, config_file_path: str = "mcp_servers.json", log_level=logging.WARNING
    ):
        """
        Create a MultiMCPClient instance from an mcp_servers.json configuration file.

        The expected format of the JSON file is:
        {
          "mcpServers": {
            "server-name": {
              "command": "command-to-run",
              "args": ["arg1", "arg2"],
              "env": {"ENV_VAR": "value"}  # Optional
            }
          }
        }

        Args:
            config_file_path: Path to the mcp_servers.json configuration file
            log_level: Logging level for the client

        Returns:
            MultiMCPClient instance

        Raises:
            FileNotFoundError: If the configuration file does not exist
            json.JSONDecodeError: If the configuration file is not valid JSON
            KeyError: If the configuration file does not have the expected structure
        """
        # Set up a logger for the class method
        logger = logging.getLogger(cls.__name__)
        logger.setLevel(log_level)

        logger.info(f"Reading MCP server configuration from {config_file_path}")

        if not os.path.exists(config_file_path):
            error_msg = f"Configuration file not found: {config_file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(config_file_path, "r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing JSON from {config_file_path}: {str(e)}"
            logger.error(error_msg)
            raise

        if "mcpServers" not in config_data:
            error_msg = f"Invalid configuration format in {config_file_path}: missing 'mcpServers' key"
            logger.error(error_msg)
            raise KeyError(error_msg)

        # Convert the mcp_servers.json format to the format expected by MultiMCPClient
        server_configs = []
        for server_name, server_config in config_data["mcpServers"].items():
            # Default to stdio type if not specified
            server_type = server_config.get("type", "stdio")

            if server_type == "stdio":
                # Extract stdio-specific connection parameters
                connection_params = {
                    "command": server_config.get("command"),
                    "args": server_config.get("args", []),
                    "env": server_config.get("env"),
                }
            elif server_type == "sse":
                # Extract SSE-specific connection parameters
                connection_params = {"url": server_config.get("url")}
            else:
                logger.warning(
                    f"Unsupported server type '{server_type}' for server '{server_name}'. Skipping."
                )
                continue

            # Add the server configuration
            server_configs.append(
                {
                    "name": server_name,
                    "type": server_type,
                    "connection_params": connection_params,
                }
            )

        logger.info(f"Found {len(server_configs)} MCP server configurations")

        # Create and return a new MultiMCPClient instance
        return await cls.create(server_configs, log_level=log_level)

    async def _initialize_servers(self, server_configs: List[Dict[str, Any]]):
        """
        Initialize connections to MCP servers based on configurations.

        Args:
            server_configs: List of server configuration dictionaries
        """
        for config in server_configs:
            name = config.get("name")
            server_type = config.get("type")
            connection_params = config.get("connection_params", {})

            if not name or not server_type:
                self.logger.error(f"Invalid server configuration: {config}")
                continue

            try:
                if server_type == "stdio":
                    await self._connect_stdio_server(name, **connection_params)
                elif server_type == "sse":
                    await self._connect_sse_server(name, **connection_params)
                else:
                    self.logger.error(f"Unsupported server type: {server_type}")
            except Exception as e:
                self.logger.error(f"Failed to connect to server {name}: {str(e)}")

    async def _connect_stdio_server(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        """
        Connect to an MCP server using stdio transport.

        Args:
            name: Server name
            command: Command to execute
            args: Command line arguments
            env: Environment variables
        """
        self.logger.info(f"Connecting to stdio server: {name}")

        server_params = StdioServerParameters(command=command, args=args or [], env=env)

        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(
                    read_stream,
                    write_stream,
                    message_handler=self._create_message_handler(name),
                )
            )

            # Initialize the session
            await session.initialize()

            self._sessions_by_name[name] = session
            self.logger.info(f"Successfully connected to stdio server: {name}")
        except Exception as e:
            self.logger.error(f"Error connecting to stdio server {name}: {str(e)}")
            raise

    async def _connect_sse_server(self, name: str, url: str):
        """
        Connect to an MCP server using SSE transport.

        Args:
            name: Server name
            url: Server URL
        """
        self.logger.info(f"Connecting to SSE server: {name} at {url}")

        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                sse_client(url)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(
                    read_stream,
                    write_stream,
                    message_handler=self._create_message_handler(name),
                )
            )

            # Initialize the session
            await session.initialize()

            self._sessions_by_name[name] = session
            self.logger.info(f"Successfully connected to SSE server: {name}")
        except Exception as e:
            self.logger.error(f"Error connecting to SSE server {name}: {str(e)}")
            raise

    def _create_message_handler(self, server_name: str):
        """Create a message handler function for a specific server."""

        async def message_handler(message):
            if isinstance(message, Exception):
                self.logger.error(f"Error from server {server_name}: {str(message)}")
            else:
                self.logger.debug(f"Message from server {server_name}: {message}")

        return message_handler

    async def disconnect(self, server_name: Optional[str] = None):
        """
        Disconnect from MCP servers.

        Args:
            server_name: Optional name of specific server to disconnect from.
                         If None, disconnects from all servers.
        """
        if server_name:
            if server_name in self._sessions_by_name:
                self.logger.info(f"Disconnecting from server: {server_name}")
                # The session will be closed when the exit stack is closed
                self._sessions_by_name.pop(server_name, None)
            else:
                self.logger.warning(f"Server not found: {server_name}")
        else:
            self.logger.info("Disconnecting from all servers")
            self._sessions_by_name.clear()

        # Close the exit stack to close all associated connections
        await self._exit_stack.aclose()

        # Create a new exit stack for future connections
        self._exit_stack = AsyncExitStack()

    async def list_functions(
        self, server_name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        List available functions/tools from MCP servers.

        Args:
            server_name: Optional name of specific server to list functions from.
                         If None, lists functions from all servers.

        Returns:
            Dictionary mapping server names to lists of function information
        """
        results = {}

        if server_name:
            if server_name in self._sessions_by_name:
                session = self._sessions_by_name[server_name]
                try:
                    tools_response = await session.list_tools()
                    results[server_name] = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "schema": tool.inputSchema,
                        }
                        for tool in tools_response.tools
                    ]
                except Exception as e:
                    self.logger.error(
                        f"Error listing functions from {server_name}: {str(e)}"
                    )
                    results[server_name] = []
            else:
                self.logger.warning(f"Server not found: {server_name}")
        else:
            # List functions from all servers
            for name, session in self._sessions_by_name.items():
                try:
                    tools_response = await session.list_tools()
                    results[name] = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "schema": tool.inputSchema,
                        }
                        for tool in tools_response.tools
                    ]
                except Exception as e:
                    self.logger.error(f"Error listing functions from {name}: {str(e)}")
                    results[name] = []

        return results

    async def call_function(
        self,
        server_name: str,
        function_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Call a function on a specific MCP server.

        Args:
            server_name: Name of the server to call the function on
            function_name: Name of the function to call
            arguments: Optional arguments to pass to the function

        Returns:
            Function result

        Raises:
            ValueError: If server is not found
            Exception: If function call fails
        """
        if server_name not in self._sessions_by_name:
            error_msg = f"Server not found: {server_name}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        session = self._sessions_by_name[server_name]
        self.logger.info(f"Calling function {function_name} on server {server_name}")
        self.logger.info(f"Arguments: {arguments}")

        # try:
        # Check if session has list_tools method to verify proper initialization
        if not hasattr(session, "call_tool"):
            error_msg = (
                f"Session for server {server_name} does not have call_tool method"
            )
            self.logger.error(error_msg)
            raise AttributeError(error_msg)

        result = await session.call_tool(function_name, arguments)
        self.logger.info(f"Function {function_name} call successful")
        return result
        # except Exception as e:
        #     error_msg = f"Error calling function {function_name} on server {server_name}: {str(e)}"
        #     self.logger.error(error_msg)
        #     # Log traceback for more detail
        #     self.logger.error(f"Traceback: {traceback.format_exc()}")
        #     raise


def load_mcp_server_configs(config_path: str = "mcp_servers.json") -> dict:
    """Load MCP server configurations from a JSON file and return the mcpServers dict."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        config = json.load(f)
        if "mcpServers" not in config:
            raise KeyError(f"Missing 'mcpServers' key in config file: {config_path}")
        return config["mcpServers"]


if __name__ == "__main__":
    import asyncio

    async def test_multi_mcp_client():
        try:
            # Initialize from config file
            print("Initializing MultiMCPClient from mcp_servers.json...")
            client = await Client.from_config_file("../../../mcp_servers.json")

            # List functions from all servers
            print("\nListing functions from all servers:")
            functions = await client.list_functions()
            for server_name, funcs in functions.items():
                if funcs:
                    print(
                        f"Server {server_name} has functions: {[f['name'] for f in funcs]}"
                    )
                else:
                    print(
                        f"Server {server_name} has no functions or failed to list them"
                    )

            # Example of calling a function on a specific server
            # Uncomment and modify this section to test an actual function call
            """
            print("\nCalling a function on a server:")
            server_name = list(functions.keys())[0]  # First server
            if functions[server_name]:
                function_name = functions[server_name][0]['name']  # First function
                print(f"Calling {function_name} on {server_name}...")
                result = await client.call_function(server_name, function_name, {"arg": "test"})
                print(f"Function result: {result}")
            """

            # Clean up
            print("\nDisconnecting...")
            await client.disconnect()
            print("Test completed successfully")

        except FileNotFoundError:
            print("Error: mcp_servers.json file not found. Please create one to test.")
        except Exception as e:
            print(f"Error during test: {str(e)}")
            # Make sure to clean up even if an error occurs
            if "client" in locals():
                await client.disconnect()

    # Run the test
    print("Starting MultiMCPClient test...")
    asyncio.run(test_multi_mcp_client())
