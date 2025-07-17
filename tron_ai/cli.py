import asyncclick as click
from rich.console import Console
from rich.prompt import Prompt as RichPrompt

from tron_ai.database.manager import DatabaseManager
from tron_ai.database.config import DatabaseConfig

from tron_ai.agents.productivity.google.agent import GoogleAgent
from tron_ai.config import setup_logging
from tron_ai.executors.agent import AgentExecutor
from tron_ai.models.config import LLMClientConfig
from tron_ai.utils.llm.LLMClient import LLMClient
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from tron_ai.models.executors import ExecutorConfig
from tron_ai.executors.completion import CompletionExecutor
from tron_ai.agents.tron.agent import TronAgent
from adalflow import OpenAIClient
import logging
import json
from mem0 import Memory
from mem0.memory.main import logger
from mem0.configs.base import MemoryConfig, VectorStoreConfig
import warnings
from tron_ai.agents.devops.ssh.agent import SSHAgent
from tron_ai.agents.productivity.todoist.agent import TodoistAgent
from tron_ai.models.agent import MissingEnvironmentVariable
from tron_ai.agents.productivity.notion.agent import NotionAgent
from tron_ai.agents.business import (
    MarketingStrategyAgent,
    SalesAgent,
    CustomerSuccessAgent,
    ProductManagementAgent,
    FinancialPlanningAgent,
    AIEthicsAgent,
    ContentCreationAgent,
    CommunityRelationsAgent,
)
from tron_ai.agents.devops.code.agent import CodeScannerAgent
from tron_ai.agents.devops.code.tools import CodeScannerTools
from rich.panel import Panel
from rich.markdown import Markdown

# Suppress Pydantic deprecation warnings from ChromaDB
warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb")


memory = Memory(config=MemoryConfig(
    history_db_path=".chroma/tron_history.db",
    vector_store=VectorStoreConfig(
        provider="chroma",
        config={
            "collection_name": "tron_memory",
            "path": ".chroma/tron_memory.db",
            
        },
    ),
    update_memory_prompt="""You are a smart memory manager which controls the memory of a system.
You can perform four operations: (1) add into the memory, (2) update the memory, (3) delete from the memory, and (4) no change.

Based on the above four operations, the memory will change.

Compare newly retrieved facts with the existing memory. For each new fact, decide whether to:
- ADD: Add it to the memory as a new element
- UPDATE: Update an existing memory element
- DELETE: Delete an existing memory element
- NONE: Make no change (if the fact is already present or irrelevant)

There are specific guidelines to select which operation to perform:

1. **Add**: If the retrieved facts contain new information not present in the memory, then you have to add it by generating a new ID in the id field.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "User is a software engineer"
            }
        ]
    - Retrieved facts: ["User's name is John"]
    - New Memory:
        {
            "memory" : [
                {
                    "id" : "0",
                    "text" : "User is a software engineer",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "User's name is John",
                    "event" : "ADD"
                }
            ]

        }

2. **Update**: If the retrieved facts contain information that is already present in the memory but the information is totally different, then you have to update it. 
If the retrieved fact contains information that conveys the same thing as the elements present in the memory, then you have to keep the fact which has the most information. 
Example (a) -- if the memory contains "User likes to play cricket" and the retrieved fact is "Loves to play cricket with friends", then update the memory with the retrieved facts.
Example (b) -- if the memory contains "Likes cheese pizza" and the retrieved fact is "Loves cheese pizza", then you do not need to update it because they convey the same information.
If the direction is to update the memory, then you have to update it.
Please keep in mind while updating you have to keep the same ID.
Please note to return the IDs in the output from the input IDs only and do not generate any new ID.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "User likes to play cricket"
            },
            {
                "id" : "1",
                "text" : "User is a software engineer"
            },
            {
                "id" : "2",
                "text" : "User likes to play cricket"
            }
        ]
    - Retrieved facts: ["User loves chicken pizza", "User loves to play cricket with friends"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "User loves chicken pizza",
                    "event" : "UPDATE",
                    "old_memory" : "User likes to play cricket"
                },
                {
                    "id" : "1",
                    "text" : "User is a software engineer",
                    "event" : "NONE"
                },
                {
                    "id" : "2",
                    "text" : "User loves to play cricket with friends",
                    "event" : "UPDATE",
                    "old_memory" : "User likes to play cricket"
                }
            ]
        }


3. **Delete**: If the retrieved facts contain information that contradicts the information present in the memory, then you have to delete it. Or if the direction is to delete the memory, then you have to delete it.
Please note to return the IDs in the output from the input IDs only and do not generate any new ID.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Name is John"
            },
            {
                "id" : "1",
                "text" : "User loves to play cricket"
            }
        ]
    - Retrieved facts: ["User dislikes to play cricket"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Name is John",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "User loves to play cricket",
                    "event" : "DELETE"
                }
        ]
        }

4. **No Change**: If the retrieved facts contain information that is already present in the memory, then you do not need to make any changes.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Name is John"
            },
            {
                "id" : "1",
                "text" : "User loves to play cricket"
            }
        ]
    - Retrieved facts: ["Name is John"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Name is John",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "User loves to play cricket",
                    "event" : "NONE"
                }
            ]
        }
    """
))

@click.group()
async def cli():
    """Command line interface for Tron AI"""
    setup_logging()


@cli.command()
@click.argument("user_query")
@click.option("--agent", default="generic", type=click.Choice(["generic", "tron", "google"]))
async def ask(user_query: str, agent: str) -> str:
    """Ask Tron AI a question"""

    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o",
            json_output=True,
        ),
    )
    
    if agent == "tron":
        agent = TronAgent()
        
        executor = AgentExecutor(
            config=ExecutorConfig(
                client=client,
                logging=True,
            ),
        )
        response = await executor.execute(user_query=user_query, agent=agent)
        
    elif agent == "google":
        agent = GoogleAgent()
        executor = AgentExecutor(
            config=ExecutorConfig(
                client=client,
                logging=True,
            ),
        )
        response = await executor.execute(user_query=user_query, agent=agent)
    else:
        executor = CompletionExecutor(
            config=ExecutorConfig(
                client=client,
                prompt=Prompt(
                    text="You are a helpful AI assistant. Help the user with their query.",
                    output_format=PromptDefaultResponse
                ),
            ),
        )
        response = await executor.execute(user_query=user_query)
    
    print(response.response)


@cli.command()
@click.argument("user_query")
@click.option("--agent", default="generic", type=click.Choice(["generic", "tron", "google", "ssh", "todoist", "notion", "marketing_strategy", "sales", "customer_success", "product_management", "financial_planning", "ai_ethics", "content_creation", "community_relations"]))
async def chat(user_query: str, agent: str):
    """Start an interactive chat session with the Tron agent."""
    import uuid
    import time
    from datetime import datetime
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.align import Align
    console = Console()
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    await db_manager.initialize()
    session_id = str(uuid.uuid4())

    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o",
            json_output=True,
        ),
    )
    
    if agent == "google":
        agent_instance = GoogleAgent()
    elif agent == "ssh":
        agent_instance = SSHAgent()
    elif agent == "todoist":
        agent_instance = TodoistAgent()
    elif agent == "notion":
        agent_instance = NotionAgent()
    elif agent == "marketing_strategy":
        agent_instance = MarketingStrategyAgent()
    elif agent == "sales":
        agent_instance = SalesAgent()
    elif agent == "customer_success":
        agent_instance = CustomerSuccessAgent()
    elif agent == "product_management":
        agent_instance = ProductManagementAgent()
    elif agent == "financial_planning":
        agent_instance = FinancialPlanningAgent()
    elif agent == "ai_ethics":
        agent_instance = AIEthicsAgent()
    elif agent == "content_creation":
        agent_instance = ContentCreationAgent()
    elif agent == "community_relations":
        agent_instance = CommunityRelationsAgent()
    else:
        agent_instance = TronAgent()
        
    executor = AgentExecutor(
        config=ExecutorConfig(
            client=client,
            logging=True,
        ),
    )
    
    # Create or get conversation
    conversation = await db_manager.get_conversation(session_id)
    if not conversation:
        conversation = await db_manager.create_conversation(
            session_id=session_id,
            user_id=None,
            agent_name=agent_instance.name,
            title=f"Chat with {agent_instance.name}",
            meta={"agent_type": agent}
        )

    # Conversation header
    header = Panel(
        f"[bold cyan]Tron AI Chat Session[/bold cyan]\n[green]Agent:[/green] {agent_instance.name}\n[dim]Type 'exit', 'quit', or 'bye' to leave.[/dim]",
        style="bold magenta",
        expand=False
    )
    console.print(header)
    triggered = False
    while True:
        try:
            if triggered:
                user_input = RichPrompt.ask("[bold green]You[/bold green]")
            else:
                user_input = user_query
                triggered = True
            if user_input.strip().lower() in ["exit", "quit", "bye"]:
                console.print(Panel("[bold yellow]Goodbye![/bold yellow]", style="yellow"))
                break
            # Get conversation history for context
            conversation_history = await db_manager.get_conversation_history(session_id, max_messages=20)
            context = ""
            if conversation_history:
                context = f"## Conversation History\n{json.dumps(conversation_history, indent=2)}"
            full_query = f"{context}\n" 
            full_query += f"User Input: {user_input}"

            # Add user message to database
            await db_manager.add_message(
                session_id=session_id,
                role="user",
                content=user_input,
                meta=None
            )
            # Show user message in a panel
            user_panel = Panel(
                Align.left(f"[bold green]You:[/bold green] {user_input}"),
                style="green",
                title=f"{datetime.now():%H:%M:%S}",
                border_style="green"
            )
            console.print(user_panel)
            # Execute agent with timing and spinner
            start_time = time.time()
            with console.status("[bold blue]Assistant is thinking...[/bold blue]", spinner="dots"):
                response = await executor.execute(user_query=full_query.rstrip(), agent=agent_instance)
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Add agent session to database
            if hasattr(response, "response") and response.response is not None:
                agent_response_val = response.response
            elif hasattr(response, "generated_output"):
                agent_response_val = response.generated_output
            else:
                agent_response_val = ""
            agent_response_str = json.dumps(agent_response_val) if isinstance(agent_response_val, dict) else str(agent_response_val)
            await db_manager.add_agent_session(
                session_id=session_id,
                agent_name=agent_instance.name,
                user_query=user_input,
                agent_response=agent_response_str,
                tool_calls=getattr(response, 'tool_calls', None),
                execution_time_ms=execution_time_ms,
                success=True,
                meta=None
            )
            # Add assistant message to database
            content = getattr(response, 'response', None)
            if not content:
                content = getattr(response, 'generated_output', "") if response is not None else ""
            else:
                content = json.dumps(content) if isinstance(content, dict) else str(content)
            await db_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=content,
                agent_name=agent_instance.name,
                tool_calls=getattr(response, 'tool_calls', None),
                meta=None
            )
            
            md_content = response.response if hasattr(response, "response") else getattr(response, "generated_output", "")

            assistant_panel = Panel(
                Markdown(md_content),
                style="blue",
                title=f"{agent_instance.name} [{datetime.now():%H:%M:%S}]",
                border_style="blue"
            )
            console.print(assistant_panel)
        except (KeyboardInterrupt, EOFError):
            console.print(Panel("\n[bold yellow]Goodbye![/bold yellow]", style="yellow"))
            break
        except Exception as e:
            console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", style="red"))
            # Log error to database
            await db_manager.add_agent_session(
                session_id=session_id,
                agent_name=agent_instance.name,
                user_query=user_input if 'user_input' in locals() else "Unknown",
                success=False,
                error_message=str(e),
                meta=None
            )
    await db_manager.close()


@cli.command()
@click.argument('directory')
@click.option('--output', default=None, help='Output JSON file path for the graph.')
@click.option('--store-neo4j', is_flag=True, help='Store the graph in Neo4j.')
async def scan_repo(directory: str, output: str, store_neo4j: bool):
    """Scan a local repository using CodeScannerAgent."""
    console = Console()
    try:
        agent_instance = CodeScannerAgent()
        client = LLMClient(
            client=OpenAIClient(),
            config=LLMClientConfig(
                model_name="gpt-4o",
                json_output=True,
            ),
        )
        executor = AgentExecutor(
            config=ExecutorConfig(
                client=client,
                logging=True,
            ),
        )
        query = f"Scan the directory {directory} and build a dependency graph using tree-sitter and NetworkX. Summarize the graph structure."
        response = await executor.execute(user_query=query, agent=agent_instance)
        # Build graph directly
        graph = CodeScannerTools.build_dependency_graph(directory=directory)
        response_text = f"Graph built with {len(graph.nodes)} nodes and {len(graph.edges)} edges."
        if store_neo4j:
            store_response = CodeScannerTools.store_graph_to_neo4j(graph=graph)
            response_text += f"\n{store_response}"
        console.print(Panel(Markdown(response_text), style="blue", title="Scan Results"))
        if output:
            import json
            from networkx.readwrite import json_graph
            data = json_graph.node_link_data(graph)
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)
            console.print(f"[green]Graph saved to {output}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@click.group()
def db():
    """Database management commands."""
    pass

@db.command()
async def init():
    """Initialize the database and create tables."""
    console = Console()
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
        console.print(f"[bold red]Error initializing database:[/bold red] {e}")
    finally:
        await db_manager.close()

@db.command()
@click.option("--days", default=90, help="Delete conversations older than N days")
async def cleanup(days: int):
    """Clean up old conversations."""
    console = Console()
    try:
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        deleted_count = await db_manager.cleanup_old_conversations(days)
        console.print(f"[bold green]Cleaned up {deleted_count} old conversations![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error cleaning up database:[/bold red] {e}")
    finally:
        await db_manager.close()

@db.command()
@click.option("--user-id", help="Filter by user ID")
@click.option("--agent", help="Filter by agent name")
@click.option("--days", default=30, help="Statistics for last N days")
async def stats(user_id: str = None, agent: str = None, days: int = 30):
    """Show database statistics."""
    console = Console()
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
        console.print(f"[bold red]Error getting statistics:[/bold red] {e}")
    finally:
        await db_manager.close()

@db.command()
@click.argument("session_id")
async def show(session_id: str):
    """Show conversation details."""
    console = Console()
    try:
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        conversation = await db_manager.get_conversation(session_id)
        if not conversation:
            console.print(f"[bold red]Conversation {session_id} not found![/bold red]")
            return
        console.print(f"[bold cyan]Conversation: {session_id}[/bold cyan]")
        console.print(f"  Agent: {conversation.agent_name}")
        console.print(f"  User ID: {conversation.user_id or 'Anonymous'}")
        console.print(f"  Title: {conversation.title or 'Untitled'}")
        console.print(f"  Created: {conversation.created_at}")
        console.print(f"  Updated: {conversation.updated_at}")
        console.print(f"  Active: {conversation.is_active}")
        console.print(f"  Messages: {conversation.message_count}")
        messages = await db_manager.get_messages(session_id, limit=10)
        if messages:
            console.print(f"\n[bold yellow]Recent Messages:[/bold yellow]")
            for msg in messages[-5:]:
                role_icon = "👤" if msg.role == "user" else "🤖"
                console.print(f"  {role_icon} [{msg.role}] {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
    except Exception as e:
        console.print(f"[bold red]Error showing conversation:[/bold red] {e}")
    finally:
        await db_manager.close()

def main():
    """Entry point that suppresses SystemExit traceback"""
    import sys
    import logging
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    original_stderr = sys.stderr
    try:
        cli.add_command(db)
        cli(_anyio_backend="asyncio")
    except SystemExit as e:
        if e.code == 0:
            import io
            sys.stderr = io.StringIO()
        sys.exit(e.code)
    finally:
        sys.stderr = original_stderr

if __name__ == "__main__":
    import sys
    import logging
    import warnings
    import re
    
    # Suppress all warnings and asyncio error logging for cleaner output
    warnings.filterwarnings("ignore")
    
    # Disable asyncio task exception logging that shows the "Task exception was never retrieved" error
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    
    def suppress_asyncio_shutdown_errors(exctype, value, traceback):
        # Suppress specific RuntimeError messages during shutdown
        if exctype is RuntimeError and (
            re.search(r'no running event loop', str(value)) or
            re.search(r'Event loop is closed', str(value))
        ):
            return  # Suppress
        # Call the default excepthook
        sys.__excepthook__(exctype, value, traceback)

    sys.excepthook = suppress_asyncio_shutdown_errors
    
    # Run the CLI directly without wrapping in asyncio.run
    # asyncclick handles its own async context
    main()
