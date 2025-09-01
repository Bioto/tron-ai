"""
Server management and status commands.

This module provides commands for managing A2A servers, checking Docker
compose status, and testing server connectivity.
"""

import asyncio
import docker
import httpx
import os
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import asyncclick as click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt as RichPrompt
from rich.table import Table

from tron_ai.cli.base import (
    CLIError,
    handle_cli_error,
    setup_cli_logging,
    with_error_handling
)


class ServerError(CLIError):
    """Raised when server operations fail."""
    pass


@click.command(name='status', help='Check the status of Docker Compose services.')
@with_error_handling
async def status():
    """Check the status of Docker Compose services."""
    console = Console()
    setup_cli_logging()
    
    # Define compose files to check
    compose_files = [
        {
            "name": "MCP Services",
            "file": ".docker/mcp/docker-compose.yml",
            "project_name": "mcp"
        },
        {
            "name": "Tron Services", 
            "file": ".docker/tron-compose.yml",
            "project_name": "docker"
        }
    ]
    
    # Create table for results
    table = Table(title="Docker Compose Services Status")
    table.add_column("Service Group", style="cyan", no_wrap=True)
    table.add_column("Service Name", style="magenta")
    table.add_column("Container Name", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Ports", style="green")
    
    overall_status = True
    
    try:
        # Initialize Docker client
        docker_socket = _get_docker_socket()
        
        if docker_socket and docker_socket.startswith('unix://'):
            client = docker.DockerClient(base_url=docker_socket)
        else:
            client = docker.from_env()
        
        for compose_config in compose_files:
            overall_status = _check_compose_services(
                client, compose_config, table
            ) and overall_status
        
    except docker.errors.DockerException as e:
        table.add_row(
            "Docker Error",
            "Connection failed",
            "N/A",
            f"[red]Cannot connect to Docker: {str(e)}[/red]",
            "N/A"
        )
        overall_status = False
    except Exception as e:
        table.add_row(
            "System Error",
            "Unknown error",
            "N/A",
            f"[red]{str(e)}[/red]",
            "N/A"
        )
        overall_status = False
    
    console.print(table)
    
    # Display overall status
    _display_overall_status(console, overall_status)
    
    # Show helpful commands
    _display_helpful_commands(console)


def _get_docker_socket() -> Optional[str]:
    """Get Docker socket from current context."""
    try:
        result = subprocess.run(
            ['docker', 'context', 'ls', '--format', '{{.Current}} {{.DockerEndpoint}}'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('true '):
                    return line.split(' ', 1)[1]
    except Exception:
        pass
    return None


def _check_compose_services(client, compose_config: Dict, table: Table) -> bool:
    """Check status of services in a compose file."""
    compose_file = compose_config["file"]
    service_group = compose_config["name"]
    project_name = compose_config["project_name"]
    
    if not os.path.exists(compose_file):
        table.add_row(
            service_group,
            "N/A",
            "N/A",
            "[red]File not found[/red]",
            "N/A"
        )
        return False
    
    try:
        # Parse compose file
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services_in_compose = list(compose_data.get('services', {}).keys())
        found_services = []
        overall_status = True
        
        # Get all containers
        containers = client.containers.list(all=True)
        
        for container in containers:
            if _container_matches_project(container, project_name, compose_file, services_in_compose):
                service_name = container.labels.get('com.docker.compose.service', container.name)
                status_display, is_healthy = _get_container_status(container)
                ports_display = _get_container_ports(container)
                
                table.add_row(
                    service_group if not found_services else "",
                    service_name,
                    container.name,
                    status_display,
                    ports_display
                )
                found_services.append(service_name)
                overall_status = overall_status and is_healthy
        
        # Check for missing services
        missing_services = set(services_in_compose) - set(found_services)
        for missing_service in missing_services:
            table.add_row(
                service_group if not found_services else "",
                missing_service,
                "N/A",
                "[yellow]Not created[/yellow]",
                "N/A"
            )
            overall_status = False
        
        # Handle case with no services
        if not found_services and not missing_services:
            table.add_row(
                service_group,
                "No services",
                "N/A",
                "[yellow]Not running[/yellow]",
                "N/A"
            )
            overall_status = False
        
        return overall_status
        
    except yaml.YAMLError as e:
        table.add_row(
            service_group,
            "YAML Error",
            "N/A",
            f"[red]Parse error: {str(e)}[/red]",
            "N/A"
        )
        return False
    except Exception as e:
        table.add_row(
            service_group,
            "Error",
            "N/A",
            f"[red]{str(e)}[/red]",
            "N/A"
        )
        return False


def _container_matches_project(container, project_name: str, compose_file: str, services_in_compose: List[str]) -> bool:
    """Check if container belongs to the project."""
    labels = container.labels
    
    # Check compose project label
    if labels.get('com.docker.compose.project') == project_name:
        config_files = labels.get('com.docker.compose.project.config_files', '')
        full_compose_path = os.path.abspath(compose_file)
        if (full_compose_path in config_files or 
            compose_file in config_files or 
            os.path.basename(compose_file) in config_files):
            return True
    
    # Fallback: check container name matches service and no conflicting labels
    if not labels.get('com.docker.compose.project') and container.name in services_in_compose:
        return True
    
    return False


def _get_container_status(container) -> tuple[str, bool]:
    """Get container status display and health status."""
    if container.status == 'running':
        return "[green]Running[/green]", True
    elif container.status in ['exited', 'stopped']:
        return "[red]Stopped[/red]", False
    elif container.status == 'paused':
        return "[yellow]Paused[/yellow]", False
    else:
        return f"[yellow]{container.status}[/yellow]", False


def _get_container_ports(container) -> str:
    """Get container port mappings display."""
    ports = []
    if container.ports:
        for container_port, host_ports in container.ports.items():
            if host_ports:
                for host_port in host_ports:
                    ports.append(f"{host_port['HostPort']}:{container_port}")
            else:
                ports.append(container_port)
    
    return ", ".join(ports) if ports else "N/A"


def _display_overall_status(console: Console, overall_status: bool) -> None:
    """Display overall status summary."""
    if overall_status:
        status_panel = Panel(
            "[bold green]✓ All services are running[/bold green]",
            style="green",
            title="Overall Status"
        )
    else:
        status_panel = Panel(
            "[bold red]✗ Some services are not running[/bold red]",
            style="red", 
            title="Overall Status"
        )
    
    console.print("\n")
    console.print(status_panel)


def _display_helpful_commands(console: Console) -> None:
    """Display helpful Docker commands."""
    help_text = """
**Useful Commands:**
- Start MCP services: `docker compose -f .docker/mcp/docker-compose.yml up -d`
- Start Tron services: `docker compose -f .docker/tron-compose.yml up -d`
- Stop MCP services: `docker compose -f .docker/mcp/docker-compose.yml down`
- Stop Tron services: `docker compose -f .docker/tron-compose.yml down`
- View logs: `docker compose -f <compose-file> logs -f`
- List all containers: `docker ps -a`
- Neo4j web interface: http://localhost:7474 (user: neo4j, pass: password)
    """
    
    console.print(Panel(Markdown(help_text), title="Quick Commands", style="dim"))


@click.command(name='list-mcp-agents')
@with_error_handling
async def list_mcp_agents():
    """List all available MCP (Model Context Protocol) agents."""
    console = Console()
    setup_cli_logging()
    
    try:
        from tron_ai.modules.mcp.manager import MCPAgentManager
        
        # Initialize MCP agent manager
        manager = MCPAgentManager()
        await manager.initialize()
        
        if not manager.agents:
            console.print(Panel(
                "[yellow]No MCP agents found![/yellow]\n\n"
                "Check your mcp_servers.json configuration file.",
                title="MCP Agents",
                style="yellow"
            ))
            return
        
        # Create main table for agents
        table = Table(title="🤖 Discovered MCP Agents", show_header=True, header_style="bold magenta")
        table.add_column("Agent Name", style="cyan", no_wrap=True)
        table.add_column("Server", style="green")
        table.add_column("Description", style="white")
        table.add_column("Tools Count", justify="center", style="yellow")
        table.add_column("Status", justify="center")
        
        for server_name, agent in manager.agents.items():
            tool_count = len(agent.tool_manager.tools) if agent.tool_manager else 0
            status = "✅ Active" if agent.mcp_client else "❌ Disconnected"
            status_style = "green" if agent.mcp_client else "red"
            
            table.add_row(
                agent.name,
                server_name,
                agent.description,
                str(tool_count),
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        console.print(table)
        console.print()
        
        # Show detailed tool information
        _display_mcp_tools(console, manager)
        
        # Summary
        _display_mcp_summary(console, manager)
        
    except Exception as e:
        console.print(Panel(
            f"[bold red]Error:[/bold red] {str(e)}\n\n"
            "Make sure your MCP servers are properly configured and accessible.",
            title="❌ Error",
            style="red"
        ))
    finally:
        try:
            if 'manager' in locals():
                await manager.cleanup()
        except Exception:
            pass


def _display_mcp_tools(console: Console, manager) -> None:
    """Display detailed tool information for MCP agents."""
    for server_name, agent in manager.agents.items():
        if agent.tool_manager and agent.tool_manager.tools:
            tool_table = Table(
                title=f"🛠️  Tools for {agent.name} ({server_name})",
                show_header=True,
                header_style="bold blue"
            )
            tool_table.add_column("Tool Name", style="cyan")
            tool_table.add_column("Description", style="white", max_width=60)
            
            for tool in agent.tool_manager.tools:
                tool_name = tool.fn.__name__
                tool_desc = tool.fn.__doc__ or "No description available"
                tool_desc = tool_desc.split('\n')[0].strip()
                tool_table.add_row(tool_name, tool_desc)
            
            console.print(tool_table)
            console.print()


def _display_mcp_summary(console: Console, manager) -> None:
    """Display MCP agents summary."""
    total_agents = len(manager.agents)
    total_tools = sum(
        len(agent.tool_manager.tools) if agent.tool_manager else 0 
        for agent in manager.agents.values()
    )
    
    summary = Panel(
        f"[bold green]Total Agents:[/bold green] {total_agents}\n"
        f"[bold blue]Total Tools:[/bold blue] {total_tools}\n\n"
        f"[dim]Configuration file: mcp_servers.json[/dim]",
        title="📊 Summary",
        style="green"
    )
    console.print(summary)


@click.command(name='start-a2a-server')
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to bind the server to")
@click.option("--include-mcp", is_flag=True, default=True, help="Include MCP agents in A2A server")
@with_error_handling
async def start_a2a_server(host: str, port: int, include_mcp: bool):
    """Start the Agent-to-Agent (A2A) communication server."""
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
        raise ServerError(
            "A2A server functionality needs to be refactored for the new CLI structure. "
            "Please use the original CLI for now: python -m tron_ai.cli start-a2a-server"
        )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        raise ServerError(f"Failed to start A2A server: {e}") from e


@click.command(name='test-a2a-server')
@click.argument("message", required=False, default="Hello, what can you help me with?")
@click.option("--host", default="127.0.0.1", help="A2A server host")
@click.option("--port", default=8000, help="A2A server port")
@click.option("--timeout", default=30, help="Request timeout in seconds")
@with_error_handling
async def test_a2a_server(message: str, host: str, port: int, timeout: int):
    """Test connectivity and response from the A2A server."""
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
        raise ServerError(f"A2A server test failed: {e}") from e


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


@click.command(name='test-a2a-interactive')
@click.option("--host", default="127.0.0.1", help="A2A server host")
@click.option("--port", default=8000, help="A2A server port")
@with_error_handling
async def test_a2a_interactive(host: str, port: int):
    """Start an interactive testing session with the A2A server."""
    console = Console()
    setup_cli_logging()
    
    console.print(Panel(
        f"[bold cyan]🚀 Interactive A2A Client[/bold cyan]\n"
        f"[green]Server:[/green] http://{host}:{port}\n"
        f"[dim]Interactive A2A testing functionality needs to be implemented.[/dim]",
        title="Interactive Session",
        style="cyan"
    ))
    
    raise ServerError(
        "Interactive A2A client functionality needs to be refactored for the new CLI structure. "
        "Please use the original CLI for now: python -m tron_ai.cli test-a2a-interactive"
    )
