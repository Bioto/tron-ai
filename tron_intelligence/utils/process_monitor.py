"""Async process monitoring utilities for efficient subprocess management."""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional, List, Callable
import time
from datetime import datetime
import signal
import psutil

logger = logging.getLogger(__name__)


class ProcessInfo:
    """Information about a monitored process."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        command: str,
        args: List[str],
        server_name: str,
    ):
        self.process = process
        self.command = command
        self.args = args
        self.server_name = server_name
        self.started_at = time.time()
        self.pid = process.pid
        self.stdout_buffer = []
        self.stderr_buffer = []
        self.return_code: Optional[int] = None
        self.terminated = False

    @property
    def is_running(self) -> bool:
        """Check if process is still running."""
        return self.return_code is None and not self.terminated

    @property
    def uptime(self) -> float:
        """Get process uptime in seconds."""
        return time.time() - self.started_at

    def get_stats(self) -> Dict[str, Any]:
        """Get process statistics."""
        stats = {
            "pid": self.pid,
            "server_name": self.server_name,
            "command": self.command,
            "args": self.args,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat(),
            "uptime_seconds": self.uptime,
            "is_running": self.is_running,
            "return_code": self.return_code,
        }

        # Try to get system stats if process is running
        if self.is_running and self.pid:
            try:
                proc = psutil.Process(self.pid)
                stats.update(
                    {
                        "cpu_percent": proc.cpu_percent(interval=0.1),
                        "memory_mb": proc.memory_info().rss / 1024 / 1024,
                        "num_threads": proc.num_threads(),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return stats


class ProcessMonitor:
    """Async process monitor that efficiently manages subprocess I/O."""

    def __init__(self, max_buffer_lines: int = 1000):
        self._processes: Dict[str, ProcessInfo] = {}
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        self._max_buffer_lines = max_buffer_lines
        self._output_callbacks: List[Callable[[str, str, str], None]] = []
        self._termination_callbacks: List[Callable[[str, int], None]] = []
        self._shutdown = False

    def add_output_callback(self, callback: Callable[[str, str, str], None]):
        """Add callback for process output (server_name, stream_type, line)."""
        self._output_callbacks.append(callback)

    def add_termination_callback(self, callback: Callable[[str, int], None]):
        """Add callback for process termination (server_name, return_code)."""
        self._termination_callbacks.append(callback)

    async def start_process(
        self,
        server_name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> ProcessInfo:
        """Start a process and begin monitoring it asynchronously."""
        # Check if process already exists
        if server_name in self._processes:
            existing = self._processes[server_name]
            if existing.is_running:
                logger.warning(f"Process for {server_name} is already running")
                return existing
            else:
                # Clean up old process
                await self.stop_process(server_name)

        # Prepare environment
        process_env = {**os.environ}
        if env:
            process_env.update(env)
        process_env["MCP_PERSISTENT_MODE"] = "1"

        # Prepare command
        full_command = [command] + (
            args if isinstance(args, list) else [args] if args else []
        )

        logger.info(
            f"Starting async process for {server_name}: {' '.join(full_command)}"
        )

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=cwd,
                # Ensure proper signal handling
                preexec_fn=None if sys.platform == "win32" else os.setsid,
            )

            # Create process info
            process_info = ProcessInfo(process, command, args, server_name)
            self._processes[server_name] = process_info

            # Start monitoring task
            monitor_task = asyncio.create_task(
                self._monitor_process(process_info), name=f"monitor_{server_name}"
            )
            self._monitor_tasks[server_name] = monitor_task

            # For very short-lived processes, give a minimal time to run
            # but don't fail if they complete quickly with success
            await asyncio.sleep(0.01)

            # Check if process has already completed
            if process.returncode is not None:
                # Process completed very quickly
                if process.returncode == 0:
                    logger.info(
                        f"Process for {server_name} completed successfully (exit code 0)"
                    )
                    # Let the monitor task handle the cleanup
                    return process_info
                else:
                    logger.error(
                        f"Process for {server_name} failed with exit code {process.returncode}"
                    )
                    raise RuntimeError(
                        f"Process failed with exit code {process.returncode}"
                    )
            else:
                logger.info(
                    f"Process for {server_name} started successfully (PID: {process.pid})"
                )
                return process_info

        except Exception as e:
            logger.error(f"Failed to start process for {server_name}: {str(e)}")
            # Clean up
            if server_name in self._processes:
                del self._processes[server_name]
            if server_name in self._monitor_tasks:
                self._monitor_tasks[server_name].cancel()
                del self._monitor_tasks[server_name]
            raise

    async def _monitor_process(self, process_info: ProcessInfo):
        """Monitor a process for output and termination."""
        server_name = process_info.server_name
        process = process_info.process

        try:
            # Create tasks for reading stdout and stderr concurrently
            stdout_task = asyncio.create_task(
                self._read_stream(process_info, process.stdout, "stdout")
            )
            stderr_task = asyncio.create_task(
                self._read_stream(process_info, process.stderr, "stderr")
            )

            # Wait for process to complete and streams to be read
            await asyncio.gather(
                process.wait(), stdout_task, stderr_task, return_exceptions=True
            )

            # Process has terminated
            process_info.return_code = process.returncode
            process_info.terminated = True

            logger.info(
                f"Process for {server_name} terminated with code {process.returncode}"
            )

            # Call termination callbacks
            for callback in self._termination_callbacks:
                try:
                    callback(server_name, process.returncode)
                except Exception as e:
                    logger.error(f"Error in termination callback: {str(e)}")

        except asyncio.CancelledError:
            logger.info(f"Monitor task for {server_name} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error monitoring process for {server_name}: {str(e)}")
        finally:
            # Clean up
            if server_name in self._monitor_tasks:
                del self._monitor_tasks[server_name]

    async def _read_stream(self, process_info: ProcessInfo, stream, stream_type: str):
        """Read from a process stream asynchronously."""
        server_name = process_info.server_name
        buffer = (
            process_info.stdout_buffer
            if stream_type == "stdout"
            else process_info.stderr_buffer
        )

        try:
            while not self._shutdown:
                # Read line with timeout to allow periodic checks
                try:
                    line_bytes = await asyncio.wait_for(stream.readline(), timeout=0.5)
                except asyncio.TimeoutError:
                    # Check if process is still running
                    if process_info.process.returncode is not None:
                        break
                    continue

                if not line_bytes:
                    break

                try:
                    line = line_bytes.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    line = str(line_bytes).rstrip()

                # Add to buffer
                buffer.append(line)
                if len(buffer) > self._max_buffer_lines:
                    buffer.pop(0)

                # Log the output
                if stream_type == "stdout":
                    logger.debug(f"[{server_name}:stdout] {line}")
                else:
                    logger.info(f"[{server_name}:stderr] {line}")

                # Call output callbacks
                for callback in self._output_callbacks:
                    try:
                        callback(server_name, stream_type, line)
                    except Exception as e:
                        logger.error(f"Error in output callback: {str(e)}")

        except Exception as e:
            logger.error(f"Error reading {stream_type} for {server_name}: {str(e)}")

    async def stop_process(self, server_name: str, timeout: float = 5.0) -> bool:
        """Stop a process gracefully with timeout."""
        if server_name not in self._processes:
            return True

        process_info = self._processes[server_name]
        if not process_info.is_running:
            # Already stopped
            del self._processes[server_name]
            return True

        process = process_info.process
        logger.info(f"Stopping process for {server_name} (PID: {process.pid})")

        try:
            # First try SIGTERM
            if sys.platform != "win32":
                process.terminate()
            else:
                process.terminate()

            # Wait for graceful termination
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
                logger.info(f"Process for {server_name} terminated gracefully")
            except asyncio.TimeoutError:
                # Force kill
                logger.warning(
                    f"Process for {server_name} did not terminate, forcing kill"
                )
                if sys.platform != "win32":
                    # Kill the entire process group
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except Exception:
                        process.kill()
                else:
                    process.kill()

                await process.wait()

            # Cancel monitor task
            if server_name in self._monitor_tasks:
                self._monitor_tasks[server_name].cancel()

            # Clean up
            del self._processes[server_name]
            return True

        except Exception as e:
            logger.error(f"Error stopping process for {server_name}: {str(e)}")
            return False

    async def stop_all_processes(self, timeout: float = 5.0):
        """Stop all processes."""
        self._shutdown = True

        # Stop all processes concurrently
        tasks = []
        for server_name in list(self._processes.keys()):
            tasks.append(self.stop_process(server_name, timeout))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error stopping process: {result}")

    def get_process_info(self, server_name: str) -> Optional[ProcessInfo]:
        """Get information about a process."""
        return self._processes.get(server_name)

    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """Get all process information."""
        return self._processes.copy()

    def is_process_running(self, server_name: str) -> bool:
        """Check if a process is running."""
        process_info = self._processes.get(server_name)
        return process_info.is_running if process_info else False

    def get_process_stats(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a process."""
        process_info = self._processes.get(server_name)
        return process_info.get_stats() if process_info else None

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all processes."""
        return {name: info.get_stats() for name, info in self._processes.items()}

    def get_process_output(
        self, server_name: str, stream_type: str = "both", lines: int = 100
    ) -> List[str]:
        """Get recent output from a process."""
        process_info = self._processes.get(server_name)
        if not process_info:
            return []

        output = []
        if stream_type in ("stdout", "both"):
            output.extend(process_info.stdout_buffer[-lines:])
        if stream_type in ("stderr", "both"):
            output.extend(process_info.stderr_buffer[-lines:])

        return output[-lines:] if stream_type == "both" else output

    async def wait_for_all_monitors(self):
        """Wait for all monitor tasks to finish (for testing/cleanup)."""
        if self._monitor_tasks:
            await asyncio.gather(*self._monitor_tasks.values(), return_exceptions=True)
