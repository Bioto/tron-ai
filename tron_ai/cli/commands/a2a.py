"""
A2A (Agent-to-Agent) server and testing commands.

This module provides commands for managing and testing the A2A communication server.
"""

import asyncio
import httpx
from uuid import uuid4
from typing import Optional

import asyncclick as click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from tron_ai.cli.base import (
    CLIError,
    handle_cli_error,
    setup_cli_logging,
    with_error_handling
)


@click.group(name='a2a', help='Agent-to-Agent (A2A) server management and testing.')
async def a2a():
    """A2A server management and testing commands."""
    pass


class A2AError(CLIError):
    """Raised when A2A operations fail."""
    pass


@a2a.command(name='start', help='Start the Agent-to-Agent (A2A) communication server.')
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to bind the server to")
@click.option("--include-mcp", is_flag=True, default=True, help="Include MCP agents in A2A server")
@with_error_handling
async def start_a2a_server(host: str, port: int, include_mcp: bool):
    """Start the A2A server with Tron agents and optionally MCP agents."""
    console = Console()
    setup_cli_logging()
    
    console.print(Panel(
        f"[bold cyan]🚀 Starting Tron AI A2A Server[/bold cyan]\n"
        f"[green]Host:[/green] {host}\n"
        f"[green]Port:[/green] {port}\n"
        f"[green]Include MCP:[/green] {'Yes' if include_mcp else 'No'}",
        title="Server Configuration",
        style="cyan"
    ))
    
    try:
        # This is a complex command that needs extensive imports
        # For now, raise a more informative error
        raise A2AError(
            "A2A server functionality needs to be refactored for the new CLI structure. "
            "Please use the original CLI for now: python -m tron_ai.cli start-a2a-server"
        )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        raise A2AError(f"Failed to start A2A server: {e}") from e


@a2a.command(name='test', help='Test connectivity and response from the A2A server.')
@click.argument("message", required=False, default="Hello, what can you help me with?")
@click.option("--host", default="127.0.0.1", help="A2A server host")
@click.option("--port", default=8000, help="A2A server port")
@click.option("--timeout", default=30, help="Request timeout in seconds")
@with_error_handling
async def test_a2a_server(message: str, host: str, port: int, timeout: int):
    """Test the A2A server by sending a message and displaying the response."""
    console = Console()
    setup_cli_logging()
    
    base_url = f'http://{host}:{port}'
    
    console.print(Panel(
        f"[bold cyan]🧪 Testing Tron A2A Server[/bold cyan]\n"
        f"[green]Server:[/green] {base_url}\n"
        f"[green]Message:[/green] {message}\n"
        f"[green]Timeout:[/green] {timeout}s",
        title="Test Configuration",
        style="cyan"
    ))
    
    try:
        await _test_a2a_connectivity(console, base_url, message, timeout)
    except Exception as e:
        raise A2AError(f"A2A server test failed: {e}") from e


async def _test_a2a_connectivity(console: Console, base_url: str, message: str, timeout: int):
    """Test A2A server connectivity and response."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        
        task = progress.add_task("🔗 Connecting to server...", total=None)
        
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            try:
                # Test basic connectivity
                response = await httpx_client.get(f"{base_url}/")
                progress.update(task, description="✅ Server is reachable")
                
                # This would need the full A2A client implementation
                # For now, just show that we can reach the server
                console.print(Panel(
                    "[bold green]✅ Basic connectivity successful![/bold green]\n\n"
                    "Full A2A testing functionality needs to be implemented.",
                    title="✅ Test Results",
                    style="green"
                ))
                
            except Exception as e:
                console.print(Panel(
                    f"[bold red]❌ Cannot connect to server:[/bold red] {str(e)}\n\n"
                    f"Make sure the A2A server is running:\n"
                    f"[cyan]tron-ai start-a2a-server --host {base_url.split('://')[1].split(':')[0]} --port {base_url.split(':')[-1]}[/cyan]",
                    title="Connection Error",
                    style="red"
                ))
                raise


@a2a.command(name='interactive', help='Start an interactive testing session with the A2A server.')
@click.option("--host", default="127.0.0.1", help="A2A server host")
@click.option("--port", default=8000, help="A2A server port")
@with_error_handling
async def test_a2a_interactive(host: str, port: int):
    """Start an interactive session with the A2A server."""
    console = Console()
    setup_cli_logging()
    
    console.print(Panel(
        f"[bold cyan]🚀 Interactive A2A Client[/bold cyan]\n"
        f"[green]Server:[/green] http://{host}:{port}\n"
        f"[dim]Interactive A2A testing functionality needs to be implemented.[/dim]",
        title="Interactive Session",
        style="cyan"
    ))
    
    raise A2AError(
        "Interactive A2A client functionality needs to be refactored for the new CLI structure. "
        "Please use the original CLI for now: python -m tron_ai.cli test-a2a-interactive"
    )
