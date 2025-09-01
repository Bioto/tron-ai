"""
Repository scanning commands.

This module provides commands for scanning and monitoring repositories
for dependency analysis and code insights.
"""

import asyncio
import json
import os
import subprocess
from typing import Optional

import asyncclick as click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from tron_ai.cli.base import (
    CLIError,
    handle_cli_error,
    setup_cli_logging,
    with_error_handling
)


@click.group(name='scan', help='Repository scanning and dependency analysis.')
async def scan():
    """Repository scanning and dependency analysis commands."""
    pass


class RepoScanError(CLIError):
    """Raised when repository scanning fails."""
    pass


@scan.command(name='repo', help='Scan a repository to analyze code dependencies and structure.')
@click.argument('directory')
@click.option('--output', default=None, help='Output JSON file path for the graph.')
@click.option('--store-neo4j', is_flag=True, help='Store the graph in Neo4j.')
@with_error_handling
async def scan_repo(directory: str, output: Optional[str], store_neo4j: bool):
    """Scan a local repository using CodeScannerAgent."""
    console = Console()
    setup_cli_logging()
    
    # Validate directory exists
    if not os.path.exists(directory):
        raise RepoScanError(f"Directory '{directory}' does not exist")
    
    if not os.path.isdir(directory):
        raise RepoScanError(f"'{directory}' is not a directory")
    
    try:
        from tron_ai.agents.devops.code_scanner.tools import CodeScannerTools
        
        # Build dependency graph
        with console.status(f"[bold blue]Scanning repository: {directory}[/bold blue]", spinner="dots"):
            graph = CodeScannerTools.build_dependency_graph(directory=directory)
        
        response_text = f"Graph built with {len(graph.nodes)} nodes and {len(graph.edges)} edges."
        
        # Store in Neo4j if requested
        if store_neo4j:
            with console.status("[bold blue]Storing graph in Neo4j...[/bold blue]", spinner="dots"):
                store_response = CodeScannerTools.store_graph_to_neo4j(graph=graph)
            response_text += f"\n{store_response}"
        
        # Save to file if requested
        if output:
            try:
                from networkx.readwrite import json_graph
                data = json_graph.node_link_data(graph)
                with open(output, 'w') as f:
                    json.dump(data, f, indent=2)
                console.print(f"[green]Graph saved to {output}[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to save graph to {output}: {e}[/yellow]")
        
        # Display results
        console.print(Panel(
            Markdown(response_text), 
            style="blue", 
            title="📊 Scan Results"
        ))
        
    except ImportError as e:
        raise RepoScanError(f"Code scanner tools not available: {e}") from e
    except Exception as e:
        raise RepoScanError(f"Failed to scan repository: {e}") from e


@scan.command(name='watch', help='Monitor a repository and scan for changes periodically.')
@click.argument('directory')
@click.option('--interval', default=300, help='Scan interval in seconds (default: 5 min).')
@click.option('--store-neo4j', is_flag=True, help='Store updates in Neo4j.')
@with_error_handling
async def scan_repo_watch(directory: str, interval: int, store_neo4j: bool):
    """Watch and periodically scan a repository for updates."""
    console = Console()
    setup_cli_logging()
    
    # Validate directory exists
    if not os.path.exists(directory):
        raise RepoScanError(f"Directory '{directory}' does not exist")
    
    if not os.path.isdir(directory):
        raise RepoScanError(f"'{directory}' is not a directory")
    
    # Check if it's a git repository
    if not os.path.exists(os.path.join(directory, '.git')):
        console.print(f"[yellow]Warning: {directory} is not a git repository. Change detection may not work properly.[/yellow]")
    
    console.print(Panel(
        f"[bold blue]Watching {directory} every {interval} seconds...[/bold blue]\n"
        f"[dim]Press Ctrl+C to stop.[/dim]",
        title="🔍 Repository Watcher",
        style="blue"
    ))
    
    async def scan_task():
        while True:
            try:
                # Check for changes using git status
                result = subprocess.run(
                    ['git', '-C', directory, 'status', '--porcelain'], 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
                
                changed = result.stdout.strip() != ''
                
                if changed:
                    console.print("[yellow]Changes detected! Running scan...[/yellow]")
                    
                    try:
                        from tron_ai.agents.devops.code_scanner.tools import CodeScannerTools
                        
                        # Reuse scan logic
                        with console.status("[bold blue]Scanning changes...[/bold blue]", spinner="dots"):
                            graph = CodeScannerTools.build_dependency_graph(directory=directory)
                        
                        summary = f"Updated graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges."
                        
                        if store_neo4j:
                            store_response = CodeScannerTools.store_graph_to_neo4j(graph=graph)
                            summary += f"\n{store_response}"
                        
                        console.print(Panel(
                            summary, 
                            style="blue", 
                            title="📊 Update Summary"
                        ))
                        
                    except Exception as scan_error:
                        console.print(f"[red]Scan error: {scan_error}[/red]")
                else:
                    console.print("[dim]No changes detected.[/dim]")
                
                await asyncio.sleep(interval)
                
            except subprocess.TimeoutExpired:
                console.print("[red]Git status command timed out[/red]")
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping repository watcher...[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error during scan: {e}[/red]")
                await asyncio.sleep(interval)
    
    try:
        await scan_task()
    except KeyboardInterrupt:
        console.print(Panel(
            "[bold yellow]Repository watcher stopped.[/bold yellow]",
            title="👋 Goodbye",
            style="yellow"
        ))
