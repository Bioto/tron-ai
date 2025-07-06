import logging
import threading
from typing import Any, Dict, List, Optional
import time

from tron_ai.modules.mcp.utils.loop import EventLoopManager
from tron_ai.utils.concurrency.process_monitor import ProcessMonitor

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Manages a pool of MCP server connections.
    Handles connection lifecycle, validation, and reconnection.
    """

    def __init__(self, event_loop_manager: EventLoopManager):
        self._event_loop = event_loop_manager
        self._connections = {}  # server_name -> connection
        self._processes = {}  # server_name -> process_info (DEPRECATED - for compatibility)
        self._process_monitor = ProcessMonitor()  # New async process monitor
        self._connection_lock = threading.Lock()
        self._process_lock = threading.Lock()
        self._server_configs = {}  # server_name -> config
        self._reconnect_attempts = {}  # server_name -> count
        self._max_reconnect_attempts = 3
        self._reconnect_backoff = 5  # seconds between reconnect attempts

        # Set up callbacks for process monitoring
        self._process_monitor.add_termination_callback(self._handle_process_termination)

    def _handle_process_termination(self, server_name: str, return_code: int):
        """Handle process termination callback."""
        logger.info(
            f"Server process for {server_name} terminated with code {return_code}"
        )
        # Clean up connection when process terminates
        with self._connection_lock:
            if server_name in self._connections:
                del self._connections[server_name]

    def set_server_configs(self, server_configs: Dict[str, Any]):
        """Set the server configurations for all managed connections"""
        self._server_configs = server_configs

    def get_connection(self, server_name: str) -> Optional[Any]:
        """
        Get a connection to the specified server, starting the process if needed.

        Args:
            server_name: Name of the server to connect to

        Returns:
            Connection object or None if connection failed
        """
        with self._connection_lock:
            # Check if we already have a connection
            if server_name in self._connections:
                # Verify the connection is still valid
                connection = self._connections[server_name]
                if self._event_loop.run_sync(
                    lambda: self._verify_connection(server_name, connection)
                ):
                    return connection
                else:
                    # Connection is invalid, remove it
                    logger.warning(
                        f"Connection to {server_name} is invalid, reconnecting"
                    )
                    del self._connections[server_name]

            # Get server config
            config = self._server_configs.get(server_name)
            if not config:
                logger.error(f"No configuration found for server {server_name}")
                return None

            # Ensure process is running
            if not self._ensure_server_process(server_name, config):
                logger.error(f"Failed to ensure server process for {server_name}")
                return None

            # Attempt to create connection
            max_retries = 3
            retry_count = 0
            last_error = None

            while retry_count < max_retries:
                try:
                    # Create connection in the event loop
                    connection = self._event_loop.run_sync(
                        lambda: self._create_connection(server_name, config)
                    )

                    if connection:
                        # Store the connection
                        self._connections[server_name] = connection
                        logger.info(f"Successfully connected to {server_name}")
                        return connection
                    else:
                        raise ValueError("Connection creation returned None")

                except Exception as e:
                    last_error = e
                    retry_count += 1
                    logger.warning(
                        f"Failed to connect to {server_name} (attempt {retry_count}/{max_retries}): {str(e)}"
                    )

                    if retry_count < max_retries:
                        # Wait before retrying with exponential backoff
                        time.sleep(0.5 * (2**retry_count))
                        # Ensure process is still running
                        if not self._ensure_server_process(server_name, config):
                            logger.error(
                                f"Server process for {server_name} is not running"
                            )
                            break

            # All retries failed
            logger.error(
                f"Failed to connect to {server_name} after {max_retries} attempts: {str(last_error)}"
            )
            return None

    async def _verify_connection(self, server_name: str, connection) -> bool:
        """
        Verify that a connection is still valid.

        Args:
            server_name: Name of the server
            connection: Connection to verify

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to list tools as a health check
            await connection.list_tools()
            return True
        except Exception as e:
            logger.debug(f"Connection verification failed for {server_name}: {str(e)}")
            return False

    async def _create_connection(
        self, server_name: str, config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Create a connection to an MCP server.

        Args:
            server_name: Name of the server
            config: Server configuration

        Returns:
            Connection object or None if failed
        """
        try:
            # Set up server parameters for stdio client
            command = config.get("command")
            args = config.get("args", [])

            if not command:
                logger.error(f"No command specified for server {server_name}")
                return None

            # Build full command
            if isinstance(args, list):
                full_command = [command] + args
            else:
                full_command = [command, args] if args else [command]

            server_params = StdioServerParameters(
                command=full_command[0],
                args=full_command[1:] if len(full_command) > 1 else [],
                env=None,
            )

            # Connect using stdio client
            logger.info(f"Attempting to establish stdio connection to {server_name}")
            try:
                async with stdio_client(server_params) as (read, write):
                    logger.info(f"Established stdio connection to {server_name}")

                    # Create client session
                    logger.info(f"Creating client session for {server_name}")
                    async with ClientSession(read, write) as session:
                        # Initialize the session
                        logger.info(f"Initializing session for {server_name}")
                        init_result = await session.initialize()
                        logger.info(
                            f"Initialized MCP session for {server_name}: {init_result}"
                        )

                        # Return the session object
                        return session
            except Exception as conn_error:
                logger.error(
                    f"Error during connection establishment for {server_name}: {str(conn_error)}"
                )
                return None

        except Exception as e:
            logger.error(f"Error creating connection to {server_name}: {str(e)}")
            return None

    def _ensure_server_process(self, server_name: str, config: Dict[str, Any]) -> bool:
        """Ensure a server process is running using async process monitor"""
        # Check if process is already running
        if self._process_monitor.is_process_running(server_name):
            return True

        try:
            # Get process command and args
            command = config.get("command")
            args = config.get("args", [])

            if not command:
                logger.error(f"No command specified for server {server_name}")
                return False

            # Start process using async monitor
            logger.info(
                f"Starting server process for {server_name}: {command} {' '.join(args if isinstance(args, list) else [args])}"
            )

            # Create environment for the process
            env = {"MCP_PERSISTENT_MODE": "1"}

            # Start the process in the event loop
            process_info = self._event_loop.run_sync(
                lambda: self._process_monitor.start_process(
                    server_name=server_name,
                    command=command,
                    args=args if isinstance(args, list) else [args] if args else [],
                    env=env,
                )
            )

            # Store in legacy format for compatibility
            with self._process_lock:
                self._processes[server_name] = {
                    "process": process_info,  # Store ProcessInfo object
                    "command": command,
                    "args": args,
                    "started_at": process_info.started_at,
                }

            return True

        except Exception as e:
            logger.error(f"Error starting server process for {server_name}: {str(e)}")
            return False

    def _monitor_process_output(self, server_name: str, process):
        """DEPRECATED - Kept for compatibility. Process monitoring is now handled by AsyncProcessMonitor"""
        logger.debug(
            f"Legacy monitor_process_output called for {server_name} - ignored"
        )

    def close_all(self):
        """Close all connections and terminate all processes"""
        logger.info("Closing all connections and terminating processes")

        # Close connections
        with self._connection_lock:
            for server_name, connection in list(self._connections.items()):
                try:
                    # Close connection in the event loop
                    self._event_loop.submit(
                        lambda conn=connection: self._close_connection(conn)
                    )
                except Exception as e:
                    logger.error(f"Error closing connection to {server_name}: {str(e)}")

            # Clear connections
            self._connections.clear()

        # Stop all processes using async monitor
        try:
            self._event_loop.run_sync(
                lambda: self._process_monitor.stop_all_processes(timeout=10.0)
            )
        except Exception as e:
            logger.error(f"Error stopping processes: {str(e)}")

        # Clear legacy process tracking
        with self._process_lock:
            self._processes.clear()

    async def _close_connection(self, connection):
        """Close a connection"""
        try:
            if hasattr(connection, "close"):
                await connection.close()
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")

    def get_all_server_names(self) -> List[str]:
        """Get a list of all server names from the configuration"""
        return list(self._server_configs.keys())

    def get_all_connection_statuses(self) -> Dict[str, bool]:
        """Get the status of all connections"""
        statuses = {}
        for server_name in self._server_configs.keys():
            with self._connection_lock:
                has_connection = server_name in self._connections

            if has_connection:
                # Check if the connection is valid
                try:
                    is_valid = self._event_loop.run_sync(
                        lambda: self._verify_connection(
                            server_name, self._connections[server_name]
                        )
                    )
                    statuses[server_name] = is_valid
                except Exception:
                    statuses[server_name] = False
            else:
                statuses[server_name] = False

        return statuses

    def get_process_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all managed processes"""
        return self._process_monitor.get_all_stats()

    def get_process_output(self, server_name: str, lines: int = 100) -> List[str]:
        """Get recent output from a server process"""
        return self._process_monitor.get_process_output(server_name, "both", lines)

