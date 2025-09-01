"""
Database management commands.

This module provides commands for database initialization, cleanup,
statistics, and conversation management.
"""

from typing import Optional

import asyncclick as click
from rich.console import Console
from rich.panel import Panel

from tron_ai.cli.base import (
    CLIError,
    handle_cli_error,
    setup_cli_logging,
    with_error_handling
)
from tron_ai.database.config import DatabaseConfig
from tron_ai.database.manager import DatabaseManager


class DatabaseError(CLIError):
    """Raised when database operations fail."""
    pass


@click.group()
def db():
    """Database management commands."""
    pass


@db.command(name='init')
@with_error_handling
async def init():
    """Initialize the database and create tables."""
    console = Console()
    setup_cli_logging()
    
    try:
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        console.print("[bold green]Database initialized successfully![/bold green]")
        
        stats = await db_manager.get_conversation_stats()
        console.print(f"[cyan]Database contains:[/cyan]")
        console.print(f"  - {stats['total_conversations']} conversations")
        console.print(f"  - {stats['total_messages']} messages")
        console.print(f"  - {stats['total_agent_sessions']} agent sessions")
        
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {e}") from e
    finally:
        if 'db_manager' in locals():
            await db_manager.close()


@db.command(name='cleanup')
@click.option("--days", default=90, help="Delete conversations older than N days")
@with_error_handling
async def cleanup(days: int):
    """Clean up old conversations."""
    console = Console()
    setup_cli_logging()
    
    try:
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        deleted_count = await db_manager.cleanup_old_conversations(days)
        console.print(f"[bold green]Cleaned up {deleted_count} old conversations![/bold green]")
        
    except Exception as e:
        raise DatabaseError(f"Failed to cleanup database: {e}") from e
    finally:
        if 'db_manager' in locals():
            await db_manager.close()


@db.command(name='stats')
@click.option("--user-id", help="Filter by user ID")
@click.option("--agent", help="Filter by agent name")
@click.option("--days", default=30, help="Statistics for last N days")
@with_error_handling
async def stats(user_id: Optional[str], agent: Optional[str], days: int):
    """Show database statistics."""
    console = Console()
    setup_cli_logging()
    
    try:
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        stats = await db_manager.get_conversation_stats(
            user_id=user_id,
            agent_name=agent,
            days=days
        )
        
        console.print(f"[bold cyan]Database Statistics (Last {days} days):[/bold cyan]")
        console.print(f"  Total Conversations: {stats['total_conversations']}")
        console.print(f"  Total Messages: {stats['total_messages']}")
        console.print(f"  Total Agent Sessions: {stats['total_agent_sessions']}")
        console.print(f"  Active Conversations: {stats['active_conversations']}")
        console.print(f"  Avg Messages/Conversation: {stats['avg_messages_per_conversation']:.1f}")
        console.print(f"  Successful Sessions: {stats['successful_sessions']}")
        console.print(f"  Failed Sessions: {stats['failed_sessions']}")
        console.print(f"  Avg Execution Time: {stats['avg_execution_time_ms']:.0f}ms")
        
    except Exception as e:
        raise DatabaseError(f"Failed to get statistics: {e}") from e
    finally:
        if 'db_manager' in locals():
            await db_manager.close()


@db.command(name='show')
@click.argument("session_id")
@with_error_handling
async def show(session_id: str):
    """Show conversation details."""
    console = Console()
    setup_cli_logging()
    
    try:
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        conversation = await db_manager.get_conversation(session_id)
        if not conversation:
            console.print(Panel(
                f"[bold red]Conversation {session_id} not found![/bold red]",
                title="❌ Not Found",
                style="red"
            ))
            return
        
        # Display conversation details
        console.print(f"[bold cyan]Conversation: {session_id}[/bold cyan]")
        console.print(f"  Agent: {conversation.agent_name}")
        console.print(f"  User ID: {conversation.user_id or 'Anonymous'}")
        console.print(f"  Title: {conversation.title or 'Untitled'}")
        console.print(f"  Created: {conversation.created_at}")
        console.print(f"  Updated: {conversation.updated_at}")
        console.print(f"  Active: {conversation.is_active}")
        console.print(f"  Messages: {conversation.message_count}")
        
        # Show recent messages
        messages = await db_manager.get_messages(session_id, limit=10)
        if messages:
            console.print(f"\n[bold yellow]Recent Messages:[/bold yellow]")
            for msg in messages[-5:]:
                role_icon = "👤" if msg.role == "user" else "🤖"
                content_preview = msg.content[:100] + ('...' if len(msg.content) > 100 else '')
                console.print(f"  {role_icon} [{msg.role}] {content_preview}")
                
    except Exception as e:
        raise DatabaseError(f"Failed to show conversation: {e}") from e
    finally:
        if 'db_manager' in locals():
            await db_manager.close()
