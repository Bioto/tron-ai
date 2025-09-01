"""
Server management commands.

This module provides commands for checking server status and listing MCP agents.
"""

import asyncio
import json
import os
import subprocess
from typing import Dict, List, Optional

import asyncclick as click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

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
        "docker-compose.yml",
        "docker-compose.override.yml",
        "docker-compose.dev.yml"
    ]
    
    # Check which compose files exist
    existing_files = [f for f in compose_files if os.path.exists(f)]
    
    if not existing_files:
        console.print(Panel(
            "[yellow]No Docker Compose files found in current directory.[/yellow]\n"
            "Make sure you're in the project root directory.",
            title="⚠️  No Compose Files",
            style="yellow"
        ))
        return
    
    console.print(Panel(
        f"[bold blue]Checking Docker Compose services...[/bold blue]\n"
        f"[dim]Files: {', '.join(existing_files)}[/dim]",
        title="🔍 Service Status",
        style="blue"
    ))
    
    # Check Docker Compose status
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            services = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        service_data = json.loads(line)
                        services.append({
                            'name': service_data.get('Service', 'Unknown'),
                            'status': service_data.get('State', 'Unknown'),
                            'ports': service_data.get('Ports', ''),
                            'image': service_data.get('Image', 'Unknown')
                        })
                    except json.JSONDecodeError:
                        continue
            
            if services:
                table = Table(title="🐳 Docker Services Status")
                table.add_column("Service", style="cyan", no_wrap=True)
                table.add_column("Status", style="green")
                table.add_column("Ports", style="yellow")
                table.add_column("Image", style="blue")
                
                for service in services:
                    status_style = "green" if service['status'] == 'running' else "red"
                    table.add_row(
                        service['name'],
                        f"[{status_style}]{service['status']}[/{status_style}]",
                        service['ports'] or "N/A",
                        service['image']
                    )
                
                console.print(table)
            else:
                console.print(Panel(
                    "[yellow]No services found or no services are running.[/yellow]",
                    title="📊 Results",
                    style="yellow"
                ))
        else:
            console.print(Panel(
                f"[red]Failed to get service status: {result.stderr}[/red]",
                title="❌ Error",
                style="red"
            ))
            
    except subprocess.TimeoutExpired:
        console.print(Panel(
            "[red]Docker Compose command timed out.[/red]",
            title="⏰ Timeout",
            style="red"
        ))
    except FileNotFoundError:
        console.print(Panel(
            "[red]Docker Compose not found. Make sure Docker is installed and running.[/red]",
            title="❌ Docker Not Found",
            style="red"
        ))
    except Exception as e:
        console.print(Panel(
            f"[red]Unexpected error: {e}[/red]",
            title="❌ Error",
            style="red"
        ))


@click.command(name='list-mcp-agents', help='List all available MCP (Model Context Protocol) agents.')
@with_error_handling
async def list_mcp_agents():
    """List all discovered MCP agents and their available tools."""
    console = Console()
    setup_cli_logging()
    
    try:
        from tron_ai.modules.mcp.manager import MCPAgentManager
        
        console.print(Panel(
            "[bold blue]Discovering MCP agents...[/bold blue]",
            title="🔍 MCP Discovery",
            style="blue"
        ))
        
        # Initialize MCP manager
        mcp_manager = MCPAgentManager()
        
        # Discover agents
        with console.status("[bold blue]Scanning for MCP agents...[/bold blue]", spinner="dots"):
            agents = await mcp_manager.discover_agents()
        
        if not agents:
            console.print(Panel(
                "[yellow]No MCP agents discovered.[/yellow]\n"
                "Make sure MCP servers are running and properly configured.",
                title="📊 Results",
                style="yellow"
            ))
            return
        
        # Display agent information
        for agent_name, agent_info in agents.items():
            console.print(Panel(
                f"[bold cyan]{agent_name}[/bold cyan]\n"
                f"[green]Description:[/green] {agent_info.get('description', 'No description')}\n"
                f"[green]Tools:[/green] {len(agent_info.get('tools', []))}",
                title=f"🤖 {agent_name}",
                style="cyan"
            ))
            
            # Show tools if available
            tools = agent_info.get('tools', [])
            if tools:
                tool_table = Table(title=f"Tools for {agent_name}")
                tool_table.add_column("Tool", style="cyan")
                tool_table.add_column("Description", style="white")
                
                for tool in tools:
                    tool_table.add_row(
                        tool.get('name', 'Unknown'),
                        tool.get('description', 'No description')
                    )
                
                console.print(tool_table)
        
        # Summary
        total_agents = len(agents)
        total_tools = sum(len(agent_info.get('tools', [])) for agent_info in agents.values())
        
        summary = Panel(
            f"[bold green]Discovery Complete![/bold green]\n\n"
            f"[bold blue]Total Agents:[/bold blue] {total_agents}\n"
            f"[bold blue]Total Tools:[/bold blue] {total_tools}\n\n"
            f"[dim]Configuration file: mcp_servers.json[/dim]",
            title="📊 Summary",
            style="green"
        )
        console.print(summary)
        
    except ImportError as e:
        raise ServerError(f"MCP manager not available: {e}") from e
    except Exception as e:
        raise ServerError(f"Failed to list MCP agents: {e}") from e
