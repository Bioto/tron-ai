"""
Main CLI entry point for Tron AI.

This module provides the main command group and ties together all
the modular command implementations.
"""

import logging
import os
import sys
import warnings
from typing import List

import asyncclick as click
from dotenv import load_dotenv
from rich.console import Console

from tron_ai.cli.agent_factory import get_agent_factory
from tron_ai.cli.base import setup_cli_logging
# Import commands with error handling
def _safe_import_commands():
    """Safely import commands, logging any failures."""
    commands = {}
    
    try:
        from tron_ai.cli.commands.ask import ask
        commands['ask'] = ask
    except Exception as e:
        logging.error(f"Failed to import ask command: {e}")
    
    try:
        from tron_ai.cli.commands.chat import chat
        commands['chat'] = chat
    except Exception as e:
        logging.error(f"Failed to import chat command: {e}")
    
    try:
        from tron_ai.cli.commands.database import db
        commands['db'] = db
    except Exception as e:
        logging.error(f"Failed to import database commands: {e}")
    
    try:
        from tron_ai.cli.commands.repo import scan_repo, scan_repo_watch
        commands['scan_repo'] = scan_repo
        commands['scan_repo_watch'] = scan_repo_watch
    except Exception as e:
        logging.error(f"Failed to import repo commands: {e}")
    
    try:
        from tron_ai.cli.commands.server import (
            list_mcp_agents,
            start_a2a_server,
            status,
            test_a2a_interactive,
            test_a2a_server
        )
        commands.update({
            'list_mcp_agents': list_mcp_agents,
            'start_a2a_server': start_a2a_server,
            'status': status,
            'test_a2a_interactive': test_a2a_interactive,
            'test_a2a_server': test_a2a_server,
        })
    except Exception as e:
        logging.error(f"Failed to import server commands: {e}")
    
    return commands

# Import commands
_commands = _safe_import_commands()


# Load environment variables early
load_dotenv()

# Configure environment
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["MEM0_TELEMETRY"] = "False"

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb")


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version information")
@click.pass_context
async def cli(ctx: click.Context, version: bool):
    """
    Tron AI - AI agent framework with specialized agents for business, 
    devops, and productivity tasks.
    
    \b
    Core Commands:
      ask        Ask a single question and get a response
      chat       Start an interactive chat session
      agents     List all available agents
    
    \b
    Repository Commands:
      scan-repo       Scan a repository for dependencies
      scan-repo-watch Monitor repository changes
    
    \b
    Server Commands:
      status              Check Docker service status
      start-a2a-server    Start the A2A server
      test-a2a-server     Test A2A server connectivity
      list-mcp-agents     List MCP agents
    
    \b
    Database Commands:
      db         Manage conversation database
    """
    setup_cli_logging()
    
    if version:
        console = Console()
        console.print("[bold cyan]Tron AI[/bold cyan] version 0.1.0")
        console.print("AI agent framework with multi-agent orchestration")
        return
    
    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        console = Console()
        console.print(ctx.get_help())


@cli.command()
async def agents():
    """List available agents."""
    console = Console()
    setup_cli_logging()
    
    factory = get_agent_factory(console)
    available_agents = factory.get_available_agents()
    
    console.print("[bold cyan]Available Agents:[/bold cyan]")
    console.print(f"[green]Total:[/green] {len(available_agents)} agents")
    console.print()
    
    # Group agents by category
    categories = {
        "Business": [a for a in available_agents if any(term in a for term in ["marketing", "sales", "customer", "product", "financial", "ethics", "content", "community"])],
        "DevOps": [a for a in available_agents if any(term in a for term in ["ssh", "code", "repo", "editor"])],
        "Productivity": [a for a in available_agents if any(term in a for term in ["google", "android", "todoist", "notion", "wordpress"])],
        "Core": [a for a in available_agents if a == "tron"],
    }
    
    for category, agent_list in categories.items():
        if agent_list:
            console.print(f"[bold yellow]{category}:[/bold yellow]")
            for agent in sorted(agent_list):
                console.print(f"  - {agent}")
            console.print()



# Add all successfully imported commands to the CLI group
for cmd_name, cmd_func in _commands.items():
    if cmd_func:
        # Set the command name explicitly to avoid using function names
        cmd_func.name = cmd_name.replace('_', '-')
        cli.add_command(cmd_func)

# Always add the agents command since it doesn't have problematic imports
cli.add_command(agents)


def main():
    """
    Main entry point for the CLI.
    
    This function handles asyncio setup and provides clean error handling
    with suppressed tracebacks for better user experience.
    """
    # Configure logging to reduce noise
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    
    # Store original stderr for cleanup
    original_stderr = sys.stderr
    
    try:
        # Run the CLI with asyncio backend
        cli(_anyio_backend="asyncio")
    except SystemExit as e:
        # Suppress traceback for clean exits
        if e.code == 0:
            import io
            sys.stderr = io.StringIO()
        sys.exit(e.code)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        console = Console()
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        # Handle unexpected errors
        console = Console()
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        logging.error(f"Unexpected CLI error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Restore stderr
        sys.stderr = original_stderr


if __name__ == "__main__":
    # Additional cleanup for direct execution
    import re
    
    def suppress_asyncio_shutdown_errors(exctype, value, traceback):
        """Suppress specific RuntimeError messages during shutdown."""
        if exctype is RuntimeError and (
            re.search(r'no running event loop', str(value)) or
            re.search(r'Event loop is closed', str(value))
        ):
            return  # Suppress
        # Call the default excepthook
        sys.__excepthook__(exctype, value, traceback)

    sys.excepthook = suppress_asyncio_shutdown_errors
    main()
