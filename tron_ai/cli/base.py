"""
Base CLI utilities and common functionality.

This module provides shared utilities for CLI commands including
validation, error handling, and common setup functions.
"""

import os
import logging
from typing import Optional

import asyncclick as click
from rich.console import Console
from rich.panel import Panel

from tron_ai.exceptions import TronAIError


logger = logging.getLogger(__name__)


class CLIError(TronAIError):
    """Base exception for CLI-related errors."""
    pass


class ValidationError(CLIError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(CLIError):
    """Raised when configuration is invalid or missing."""
    pass


def validate_environment() -> None:
    """
    Validate required environment variables are present.
    
    Raises:
        ConfigurationError: If required environment variables are missing
    """
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key (required for most agents)",
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var}: {description}")
    
    if missing_vars:
        error_msg = "Missing required environment variables:\n" + "\n".join(missing_vars)
        raise ConfigurationError(error_msg)


def validate_query_input(user_query: Optional[str], command_name: str) -> str:
    """
    Validate and return user query input.
    
    Args:
        user_query: User-provided query (may be None)
        command_name: Name of the command for error messages
        
    Returns:
        Validated user query string
        
    Raises:
        ValidationError: If query is invalid
    """
    if not user_query or not user_query.strip():
        raise ValidationError(
            f"Query cannot be empty for {command_name} command. "
            f"Please provide a valid query."
        )
    
    return user_query.strip()


def handle_cli_error(error: Exception, console: Console) -> None:
    """
    Handle CLI errors with appropriate user messaging.
    
    Args:
        error: The exception that occurred
        console: Rich console for output
    """
    if isinstance(error, ValidationError):
        console.print(Panel(
            f"[bold yellow]Validation Error:[/bold yellow] {error}",
            title="❌ Input Error",
            style="yellow"
        ))
    elif isinstance(error, ConfigurationError):
        console.print(Panel(
            f"[bold red]Configuration Error:[/bold red] {error}\n\n"
            f"[dim]Tip: Copy .env.example to .env and configure your API keys.[/dim]",
            title="❌ Configuration Error",
            style="red"
        ))
    elif isinstance(error, CLIError):
        console.print(Panel(
            f"[bold red]CLI Error:[/bold red] {error}",
            title="❌ Error",
            style="red"
        ))
    else:
        # Log full error for debugging but show user-friendly message
        logger.error(f"Unexpected error: {error}", exc_info=True)
        console.print(Panel(
            f"[bold red]Unexpected Error:[/bold red] {error}\n\n"
            f"[dim]Please check the logs for more details.[/dim]",
            title="❌ Unexpected Error",
            style="red"
        ))


def setup_cli_logging() -> None:
    """Setup logging configuration for CLI commands."""
    from tron_ai.config import setup_logging
    setup_logging()


def create_console() -> Console:
    """Create a configured Rich console instance."""
    return Console()


# Decorators for common CLI functionality
def with_error_handling(func):
    """Decorator to add consistent error handling to CLI commands."""
    async def wrapper(*args, **kwargs):
        console = create_console()
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            handle_cli_error(e, console)
            raise click.Abort()
    
    return wrapper


def with_validation(func):
    """Decorator to add environment validation to CLI commands."""
    async def wrapper(*args, **kwargs):
        try:
            validate_environment()
        except ConfigurationError as e:
            console = create_console()
            handle_cli_error(e, console)
            raise click.Abort()
        
        return await func(*args, **kwargs)
    
    return wrapper
