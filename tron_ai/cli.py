import os
import warnings
import logging
import json
import asyncio
import subprocess

import asyncclick as click

from rich.console import Console
from rich.prompt import Prompt as RichPrompt
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table


from tron_ai.config import setup_logging

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["MEM0_TELEMETRY"] = "False"

# Suppress Pydantic deprecation warnings from ChromaDB
warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb")

def get_update_memory_prompt():
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
    return update_memory_prompt

@click.group()
async def cli():
    """Command line interface for Tron AI"""
    setup_logging()


@cli.command()
@click.argument("user_query", required=False)
@click.option("--agent", default="generic", type=click.Choice(["generic", "tron", "google"]))
async def ask(user_query: str, agent: str) -> str:
    """Ask Tron AI a question"""
    
    from adalflow import OpenAIClient
    from tron_ai.models.config import LLMClientConfig
    from tron_ai.utils.llm.LLMClient import LLMClient
    from tron_ai.models.executors import ExecutorConfig
    from tron_ai.agents.tron.agent import TronAgent
    from tron_ai.agents.productivity.google.agent import GoogleAgent
    from tron_ai.executors.agent import AgentExecutor
    from tron_ai.models.prompts import Prompt, PromptDefaultResponse
    from tron_ai.executors.completion import CompletionExecutor
    
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
@click.argument("user_query", required=False)
@click.option("--agent", default="generic", type=click.Choice(["generic", "tron", "google", "ssh", "todoist", "notion", "wordpress", "marketing_strategy", "sales", "customer_success", "product_management", "financial_planning", "ai_ethics", "content_creation", "community_relations"]))
@click.option("--mcp-agent", default=None, help="Use a specific MCP agent by server name (e.g., 'mcp-server-docker')")
@click.option("--mode", default="regular", type=click.Choice(["regular", "swarm"]), help="Execution mode")
async def chat(agent: str, mcp_agent: str, user_query: str | None = None, mode: str = "regular"):
    """Start an interactive chat session with the Tron agent."""
    import uuid
    import time
    from datetime import datetime
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.align import Align
    from tron_ai.database.config import DatabaseConfig
    from tron_ai.database.manager import DatabaseManager
    from tron_ai.models.executors import ExecutorConfig
    from tron_ai.utils.llm.LLMClient import get_llm_client
    from tron_ai.executors.agent import AgentExecutor
    from tron_ai.executors.swarm.executor import SwarmExecutor
    from tron_ai.executors.swarm.models import SwarmState
    from adalflow.components.model_client import OpenAIClient
    
    console = Console()
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    await db_manager.initialize()
    session_id = str(uuid.uuid4())
    
    client = get_llm_client(json_output=True)
    
    # Check if an MCP agent was requested
    if mcp_agent:
        from tron_ai.modules.mcp.manager import MCPAgentManager
        try:
            manager = MCPAgentManager()
            await manager.initialize()
            agent_instance = manager.get_agent(mcp_agent)
            if not agent_instance:
                console.print(f"[bold red]MCP agent '{mcp_agent}' not found![/bold red]")
                console.print("Available MCP agents:")
                for name in manager.agents.keys():
                    console.print(f"  - {name}")
                return
        except Exception as e:
            console.print(f"[bold red]Error loading MCP agent:[/bold red] {str(e)}")
            return
    elif agent == "google":
        from tron_ai.agents.productivity.google.agent import GoogleAgent
        agent_instance = GoogleAgent()
    elif agent == "ssh":
        from tron_ai.agents.devops.ssh.agent import SSHAgent
        agent_instance = SSHAgent()
    elif agent == "todoist":
        from tron_ai.agents.productivity.todoist.agent import TodoistAgent
        agent_instance = TodoistAgent()
    elif agent == "notion":
        from tron_ai.agents.productivity.notion.agent import NotionAgent
        agent_instance = NotionAgent()
    elif agent == "marketing_strategy":
        from tron_ai.agents.business.marketing_strategy.agent import MarketingStrategyAgent
        agent_instance = MarketingStrategyAgent()
    elif agent == "sales":
        from tron_ai.agents.business.sales.agent import SalesAgent
        agent_instance = SalesAgent()
    elif agent == "customer_success":
        from tron_ai.agents.business.customer_success.agent import CustomerSuccessAgent
        agent_instance = CustomerSuccessAgent()
    elif agent == "product_management":
        from tron_ai.agents.business.product_management.agent import ProductManagementAgent
        agent_instance = ProductManagementAgent()
    elif agent == "financial_planning":
        from tron_ai.agents.business.financial_planning.agent import FinancialPlanningAgent
        agent_instance = FinancialPlanningAgent()
    elif agent == "ai_ethics":
        from tron_ai.agents.business.ai_ethics.agent import AIEthicsAgent
        agent_instance = AIEthicsAgent()
    elif agent == "content_creation":
        from tron_ai.agents.business.content_creation.agent import ContentCreationAgent
        agent_instance = ContentCreationAgent()
    elif agent == "community_relations":
        from tron_ai.agents.business.community_relations.agent import CommunityRelationsAgent
        agent_instance = CommunityRelationsAgent()
    elif agent == "wordpress":
        from tron_ai.agents.productivity.wordpress.agent import WordPressAgent
        agent_instance = WordPressAgent()
    else:
        from tron_ai.agents.tron.agent import TronAgent
        agent_instance = TronAgent(mode=mode)
        
    all_agents = []
    try:
        from tron_ai.agents.productivity.google.agent import GoogleAgent
        all_agents.append(GoogleAgent())
        console.print("[green]✓[/green] Added Google Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Google Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.productivity.todoist.agent import TodoistAgent
        all_agents.append(TodoistAgent())
        console.print("[green]✓[/green] Added Todoist Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Todoist Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.productivity.notion.agent import NotionAgent
        all_agents.append(NotionAgent())
        console.print("[green]✓[/green] Added Notion Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Notion Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.devops.ssh.agent import SSHAgent
        all_agents.append(SSHAgent())
        console.print("[green]✓[/green] Added SSH Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] SSH Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.marketing_strategy.agent import MarketingStrategyAgent
        all_agents.append(MarketingStrategyAgent())
        console.print("[green]✓[/green] Added Marketing Strategy Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Marketing Strategy Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.sales.agent import SalesAgent
        all_agents.append(SalesAgent())
        console.print("[green]✓[/green] Added Sales Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Sales Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.customer_success.agent import CustomerSuccessAgent
        all_agents.append(CustomerSuccessAgent())
        console.print("[green]✓[/green] Added Customer Success Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Customer Success Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.product_management.agent import ProductManagementAgent
        all_agents.append(ProductManagementAgent())
        console.print("[green]✓[/green] Added Product Management Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Product Management Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.financial_planning.agent import FinancialPlanningAgent
        all_agents.append(FinancialPlanningAgent())
        console.print("[green]✓[/green] Added Financial Planning Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Financial Planning Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.ai_ethics.agent import AIEthicsAgent
        all_agents.append(AIEthicsAgent())
        console.print("[green]✓[/green] Added AI Ethics Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] AI Ethics Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.content_creation.agent import ContentCreationAgent
        all_agents.append(ContentCreationAgent())
        console.print("[green]✓[/green] Added Content Creation Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Content Creation Agent unavailable: {str(e)}")
        
    try:
        from tron_ai.agents.business.community_relations.agent import CommunityRelationsAgent
        all_agents.append(CommunityRelationsAgent())
        console.print("[green]✓[/green] Added Community Relations Agent")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Community Relations Agent unavailable: {str(e)}")
        
    # Add the requested agent if it's not already in all_agents
    # Don't add TronAgent to the swarm agents list - it's the orchestrator
    if agent_instance not in all_agents and type(agent_instance).__name__ != "TronAgent":
        all_agents.append(agent_instance)
        console.print(f"[green]✓[/green] Added requested agent: {agent_instance.name}")

    # Create executor based on mode
    if mode == "regular":
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
        f"[bold cyan]Tron AI Chat Session[/bold cyan]\n[green]Agent:[/green] {agent_instance.name if mode=='regular' else 'Swarm'}\n[green]Mode:[/green] {mode}\n[dim]Type 'exit', 'quit', or 'bye' to leave.[/dim]",
        style="bold magenta",
        expand=False
    )
    console.print(header)
    triggered = user_query is None
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
                if mode == "regular":
                    response = await executor.execute(user_query=full_query.rstrip(), agent=agent_instance)
                else:
                    swarm_state = SwarmState(agents=all_agents)
                    swarm_executor = SwarmExecutor(
                        state=swarm_state,
                        config=ExecutorConfig(
                            client=client,
                            logging=True,
                        ),
                    )
                    response = await swarm_executor.execute(user_query=full_query.rstrip())
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Add agent session to database
            agent_name = "swarm" if mode == "swarm" else agent_instance.name
            if hasattr(response, "task_report") and callable(response.task_report):
                agent_response_val = response.task_report()
            elif hasattr(response, "response") and response.response is not None:
                agent_response_val = response.response
            elif hasattr(response, "generated_output"):
                agent_response_val = response.generated_output
            else:
                agent_response_val = ""
            agent_response_str = json.dumps(agent_response_val) if isinstance(agent_response_val, dict) else str(agent_response_val)
            await db_manager.add_agent_session(
                session_id=session_id,
                agent_name=agent_name,
                user_query=user_input,
                agent_response=agent_response_str,
                tool_calls=getattr(response, 'tool_calls', None),
                execution_time_ms=execution_time_ms,
                success=True,
                meta=None
            )
            # Add assistant message to database
            if hasattr(response, "task_report") and callable(response.task_report):
                md_content = response.task_report()
            elif hasattr(response, "response") and response.response:
                md_content = response.response
            elif hasattr(response, "generated_output") and response.generated_output:
                md_content = response.generated_output
            else:
                md_content = ""
            
            if isinstance(md_content, dict):
                md_content = json.dumps(md_content)
            else:
                md_content = str(md_content)
            await db_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=md_content,
                agent_name=agent_name,
                tool_calls=getattr(response, 'tool_calls', None),
                meta=None
            )
            
            if mode == "regular":
                md_content = response.response if hasattr(response, "response") else getattr(response, "generated_output", "")
            else:
                # For swarm mode, check if tasks were actually generated
                if hasattr(response, 'response') and response.response:
                    md_content = response.response
                elif hasattr(response, 'tasks') and response.tasks:
                    md_content = response.task_report()
                elif hasattr(response, 'report') and response.report:
                    md_content = response.report
                else:
                    md_content = getattr(response, "generated_output", "No response generated")

            if hasattr(response, 'tool_calls') and response.tool_calls:
                md_content += "\n\n### Diagnostic Message: Tools Used\n"
                for tc in response.tool_calls:
                    md_content += f"- **{tc['name']}**\n"
                    if 'output' in tc:
                        output_val = tc['output']
                        if isinstance(output_val, (dict, list)):
                            try:
                                pretty_output = json.dumps(output_val, indent=2)
                                if len(pretty_output) > 500:
                                    md_content += "  Output (truncated):\n```json\n" + pretty_output[:500] + "...\n```\n"
                                else:
                                    md_content += "  Output:\n```json\n" + pretty_output + "\n```\n"
                            except:
                                output_str = str(output_val)
                                if len(output_str) > 500:
                                    md_content += f"  Output (truncated): {output_str[:500]}...\n"
                                else:
                                    md_content += f"  Output: {output_str}\n"
                        else:
                            output_str = str(output_val)
                            if len(output_str) > 500:
                                md_content += f"  Output (truncated): {output_str[:500]}...\n"
                            else:
                                md_content += f"  Output: {output_str}\n"
                    if 'error' in tc:
                        error_val = tc['error']
                        if isinstance(error_val, (dict, list)):
                            try:
                                pretty_error = json.dumps(error_val, indent=2)
                                if len(pretty_error) > 500:
                                    md_content += "  Error (truncated):\n```json\n" + pretty_error[:500] + "...\n```\n"
                                else:
                                    md_content += "  Error:\n```json\n" + pretty_error + "\n```\n"
                            except:
                                error_str = str(error_val)
                                if len(error_str) > 500:
                                    md_content += f"  Error (truncated): {error_str[:500]}...\n"
                                else:
                                    md_content += f"  Error: {error_str}\n"
                        else:
                            error_str = str(error_val)
                            if len(error_str) > 500:
                                md_content += f"  Error (truncated): {error_str[:500]}...\n"
                            else:
                                md_content += f"  Error: {error_str}\n"
                    md_content += "\n"

            if hasattr(response, 'diagnostics') and response.diagnostics:
                md_content += "\n\n### Response Diagnostics\n"
                md_content += f"**Confidence Score:** {response.diagnostics.confidence:.2f}\n\n"
                md_content += "**Thoughts:**\n"
                for thought in response.diagnostics.thoughts:
                    md_content += f"- {thought}\n"
                md_content += "\n"

            assistant_panel = Panel(
                Markdown(md_content),
                style="blue",
                title=f"{agent_name} [{datetime.now():%H:%M:%S}]",
                border_style="blue"
            )
            console.print(assistant_panel)
        except (KeyboardInterrupt, EOFError):
            console.print(Panel("\n[bold yellow]Goodbye![/bold yellow]", style="yellow"))
            break
        except Exception as e:
            console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", style="red"))
            # Log error to database
            agent_name = "swarm" if mode == "swarm" else agent_instance.name
            await db_manager.add_agent_session(
                session_id=session_id,
                agent_name=agent_name,
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
    from tron_ai.agents.devops.code_scanner.tools import CodeScannerTools
    console = Console()
    try:
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


@cli.command()
@click.argument('directory')
@click.option('--interval', default=300, help='Scan interval in seconds (default: 5 min).')
@click.option('--store-neo4j', is_flag=True, help='Store updates in Neo4j.')
async def scan_repo_watch(directory: str, interval: int, store_neo4j: bool):
    """Watch and periodically scan a repository for updates."""
    from tron_ai.agents.devops.code_scanner.tools import CodeScannerTools
    console = Console()
    console.print(f"[bold blue]Watching {directory} every {interval} seconds...[/bold blue]\n[dim]Press Ctrl+C to stop.[/dim]")
    
    async def scan_task():
        while True:
            try:
                # Check for changes (simple git status)
                result = subprocess.run(['git', '-C', directory, 'status', '--porcelain'], capture_output=True, text=True)
                changed = result.stdout.strip() != ''
                if changed:
                    console.print("[yellow]Changes detected! Running scan...[/yellow]")
                    # Reuse scan logic
                    graph = CodeScannerTools.build_dependency_graph(directory=directory)
                    summary = f"Updated graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges."
                    if store_neo4j:
                        store_response = CodeScannerTools.store_graph_to_neo4j(graph=graph)
                        summary += f"\n{store_response}"
                    console.print(Panel(summary, style="blue", title="Update Summary"))
                else:
                    console.print("[dim]No changes detected.[/dim]")
                await asyncio.sleep(interval)
            except Exception as e:
                console.print(f"[red]Error during scan: {str(e)}[/red]")
    
    await scan_task()


@cli.command()
async def status():
    """Check the status of Docker Compose services."""
    import docker
    import yaml
    from pathlib import Path
    
    console = Console()
    
    # Define compose files to check
    compose_files = [
        {
            "name": "MCP Services",
            "file": ".docker/mcp/docker-compose.yml",
            "project_name": "mcp"  # docker-compose run from .docker/mcp/ 
        },
        {
            "name": "Tron Services", 
            "file": ".docker/tron-compose.yml",
            "project_name": "docker"  # docker-compose run from .docker/ directory
        }
    ]
    
    # Create a table for displaying results
    table = Table(title="Docker Compose Services Status")
    table.add_column("Service Group", style="cyan", no_wrap=True)
    table.add_column("Service Name", style="magenta")
    table.add_column("Container Name", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Ports", style="green")
    
    overall_status = True
    
    try:
        # Initialize Docker client - check for Colima or other custom contexts
        docker_socket = None
        
        # Try to get the current Docker context
        try:
            result = subprocess.run(['docker', 'context', 'ls', '--format', '{{.Current}} {{.DockerEndpoint}}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('true '):
                        docker_socket = line.split(' ', 1)[1]
                        break
        except:
            pass
        
        # Initialize Docker client with the correct socket
        if docker_socket and docker_socket.startswith('unix://'):
            client = docker.DockerClient(base_url=docker_socket)
        else:
            client = docker.from_env()
        
        for compose_config in compose_files:
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
                overall_status = False
                continue
                
            try:
                # Parse compose file to get expected services
                with open(compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f)
                
                services_in_compose = list(compose_data.get('services', {}).keys())
                found_services = []
                
                # Get all containers and filter by project
                containers = client.containers.list(all=True)
                
                for container in containers:
                    labels = container.labels
                    container_name = container.name
                    
                    # Check if container belongs to this compose project
                    # Be more specific about matching to avoid false positives
                    matches_project = False
                    
                    # First, check if it has compose labels and matches our project
                    if labels.get('com.docker.compose.project') == project_name:
                        # Verify it's from the correct compose file
                        config_files = labels.get('com.docker.compose.project.config_files', '')
                        # Normalize paths for comparison
                        full_compose_path = os.path.abspath(compose_file)
                        if full_compose_path in config_files or compose_file in config_files or os.path.basename(compose_file) in config_files:
                            matches_project = True
                    
                    # Fallback: check if container name exactly matches a service and has no conflicting labels
                    elif not labels.get('com.docker.compose.project'):
                        # Only match if container name exactly matches a service name
                        if container_name in services_in_compose:
                            matches_project = True
                    
                    if matches_project:
                        service_name = labels.get('com.docker.compose.service', container_name)
                        # If no compose service label, try to determine from container name
                        if service_name == 'Unknown':
                            # For containers without compose labels, use container name as service name
                            service_name = container_name
                        
                        # Get container status
                        if container.status == 'running':
                            status_display = "[green]Running[/green]"
                        elif container.status in ['exited', 'stopped']:
                            status_display = "[red]Stopped[/red]"
                            overall_status = False
                        elif container.status == 'paused':
                            status_display = "[yellow]Paused[/yellow]"
                            overall_status = False
                        else:
                            status_display = f"[yellow]{container.status}[/yellow]"
                            overall_status = False
                        
                        # Get port mappings
                        ports = []
                        if container.ports:
                            for container_port, host_ports in container.ports.items():
                                if host_ports:
                                    for host_port in host_ports:
                                        ports.append(f"{host_port['HostPort']}:{container_port}")
                                else:
                                    ports.append(container_port)
                        
                        ports_display = ", ".join(ports) if ports else "N/A"
                        
                        table.add_row(
                            service_group if not found_services else "",
                            service_name,
                            container_name,
                            status_display,
                            ports_display
                        )
                        found_services.append(service_name)
                
                # Check for services defined in compose but not found as containers
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
                
                # If no services found at all
                if not found_services and not missing_services:
                    table.add_row(
                        service_group,
                        "No services",
                        "N/A",
                        "[yellow]Not running[/yellow]",
                        "N/A"
                    )
                    overall_status = False
                    
            except yaml.YAMLError as e:
                table.add_row(
                    service_group,
                    "YAML Error",
                    "N/A",
                    f"[red]Parse error: {str(e)}[/red]",
                    "N/A"
                )
                overall_status = False
            except Exception as e:
                table.add_row(
                    service_group,
                    "Error",
                    "N/A",
                    f"[red]{str(e)}[/red]",
                    "N/A"
                )
                overall_status = False
                
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
    
    # Overall status summary
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
    
    # Provide helpful commands (updated for both docker-compose and docker compose)
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


@cli.command()
async def list_mcp_agents():
    """List all discovered MCP agents and their available tools."""
    from tron_ai.modules.mcp.manager import MCPAgentManager
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    try:
        # Initialize the MCP agent manager
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
            # Get tool count
            tool_count = len(agent.tool_manager.tools) if agent.tool_manager else 0
            
            # Status indicator
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
        
        # Show detailed tool information for each agent
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
                    # Clean up the description (take first line if multiline)
                    tool_desc = tool_desc.split('\n')[0].strip()
                    tool_table.add_row(tool_name, tool_desc)
                
                console.print(tool_table)
                console.print()
        
        # Summary panel
        total_agents = len(manager.agents)
        total_tools = sum(len(agent.tool_manager.tools) if agent.tool_manager else 0 
                         for agent in manager.agents.values())
        
        summary = Panel(
            f"[bold green]Total Agents:[/bold green] {total_agents}\n"
            f"[bold blue]Total Tools:[/bold blue] {total_tools}\n\n"
            f"[dim]Configuration file: mcp_servers.json[/dim]",
            title="📊 Summary",
            style="green"
        )
        console.print(summary)
        
    except Exception as e:
        console.print(Panel(
            f"[bold red]Error:[/bold red] {str(e)}\n\n"
            "Make sure your MCP servers are properly configured and accessible.",
            title="❌ Error",
            style="red"
        ))
    finally:
        # Clean up the manager
        try:
            await manager.cleanup()
        except Exception:
            pass  # Ignore cleanup errors


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind the server to")
@click.option("--port", default=8000, help="Port to bind the server to")
@click.option("--include-mcp", is_flag=True, default=True, help="Include MCP agents in A2A server")
async def start_a2a_server(host: str, port: int, include_mcp: bool):
    """Start the A2A server with Tron agents and optionally MCP agents."""
    import uvicorn
    import httpx
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
    from a2a.server.apps import A2AStarletteApplication
    from tron_ai.executors.swarm.models import SwarmResults
    from tron_ai.models.prompts import Prompt
    from tron_ai.executors.agent import AgentExecutor
    from tron_ai.models.agent import Agent
    from tron_ai.executors.base import ExecutorConfig
    from tron_ai.utils.llm.LLMClient import get_llm_client
    from tron_ai.modules.a2a.executor import TronA2AExecutor
    from rich.panel import Panel
    
    console = Console()
    
    console.print(Panel(
        f"[bold cyan]🚀 Starting Tron AI A2A Server[/bold cyan]\n"
        f"[green]Host:[/green] {host}\n"
        f"[green]Port:[/green] {port}\n"
        f"[green]Include MCP:[/green] {'Yes' if include_mcp else 'No'}",
        title="Server Configuration",
        style="cyan"
    ))
    
    try:
        # Collect all available agents
        agents = []
        
        # Core Tron agents
        from tron_ai.agents.tron.agent import TronAgent
        tron_agent = TronAgent()
        agents.append(tron_agent)
        
        # Add productivity agents
        try:
            from tron_ai.agents.productivity.google.agent import GoogleAgent
            agents.append(GoogleAgent())
            console.print("[green]✓[/green] Added Google Agent")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Google Agent unavailable: {str(e)}")
        
        try:
            from tron_ai.agents.productivity.todoist.agent import TodoistAgent
            agents.append(TodoistAgent())
            console.print("[green]✓[/green] Added Todoist Agent")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Todoist Agent unavailable: {str(e)}")
        
        try:
            from tron_ai.agents.productivity.notion.agent import NotionAgent
            agents.append(NotionAgent())
            console.print("[green]✓[/green] Added Notion Agent")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Notion Agent unavailable: {str(e)}")
        
        # Add DevOps agents
        try:
            from tron_ai.agents.devops.ssh.agent import SSHAgent
            agents.append(SSHAgent())
            console.print("[green]✓[/green] Added SSH Agent")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] SSH Agent unavailable: {str(e)}")
        
        # Add MCP agents if requested
        mcp_agents = []
        if include_mcp:
            try:
                from tron_ai.modules.mcp.manager import MCPAgentManager
                manager = MCPAgentManager()
                await manager.initialize()
                
                if manager.agents:
                    for server_name, agent in manager.agents.items():
                        agents.append(agent)
                        mcp_agents.append(agent)
                        console.print(f"[green]✓[/green] Added MCP Agent: {agent.name}")
                else:
                    console.print("[yellow]⚠[/yellow] No MCP agents found")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to load MCP agents: {str(e)}")
        
                 # Create the main orchestrator agent
        orchestrator_agent = Agent(
             name="Tron A2A Orchestrator",
             description="Helpful assistant coordinating multiple specialized agents for comprehensive task execution",
             prompt=Prompt(
                 text=f"""You are the Tron A2A Orchestrator, a helpful assistant that coordinates {len(agents)} specialized agents to help users accomplish their goals.

Available Agents:
{chr(10).join([f"- {agent.name}: {agent.description}" for agent in agents])}

Your role is to analyze user requests and either:
1. **Simple Questions**: Answer directly if it's a basic query (like math, general knowledge, simple explanations)
2. **Complex Tasks**: Break down into specific tasks and assign to appropriate agents

Response Style:
- For simple questions: Provide direct, helpful answers
- For complex tasks: Create clear task breakdowns but respond conversationally  
- Always be helpful, clear, and user-friendly
- Avoid exposing internal task structures or diagnostic information
- Focus on the user's actual needs and provide actionable information

Response Format:
- For simple questions: Set the `response` field with your direct answer and leave `tasks` empty
- For complex operations: Leave `response` empty and create appropriate `tasks`

Examples:
- User: "What's 3 + 3?" → response: "3 + 3 equals 6", tasks: []
- User: "What is Python?" → response: "Python is a programming language...", tasks: []
- User: "Check my email and create a task" → response: "", tasks: [email_task, create_task]
- User: "List my Docker containers" → response: "", tasks: [docker_list_task]

Remember: Use the `response` field for direct answers and `tasks` only when agent delegation is needed.
""",
                 output_format=SwarmResults
             ),
         )
        
        # Create executor configuration
        config = ExecutorConfig(client=get_llm_client(json_output=True), logging=True)
        
        # Create agent executor with all agents
        executor = AgentExecutor(
            config=config,
            agents=agents
        )
        
        # Create A2A executor
        a2a_executor = TronA2AExecutor(
            agent=orchestrator_agent,
            executor=executor,
            agents=agents
        )
        
        # Create HTTP client and components
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=a2a_executor,
            task_store=InMemoryTaskStore(),
            push_notifier=InMemoryPushNotifier(httpx_client),
        )
        
        # Create A2A application
        server = A2AStarletteApplication(
            agent_card=orchestrator_agent.to_a2a_card(), 
            http_handler=request_handler
        )
        
        # Display detailed agent list
        console.print()
        agent_table = Table(title="🤖 Available Agents", show_header=True, header_style="bold magenta")
        agent_table.add_column("Agent Name", style="cyan", no_wrap=True)
        agent_table.add_column("Type", style="green")
        agent_table.add_column("Description", style="white", max_width=50)
        agent_table.add_column("Tools", justify="center", style="yellow")
        
        for agent in agents:
            # Determine agent type
            agent_type = "Core"
            if agent in mcp_agents:
                agent_type = "MCP"
            elif "productivity" in agent.__class__.__module__:
                agent_type = "Productivity"
            elif "devops" in agent.__class__.__module__:
                agent_type = "DevOps"
            elif "business" in agent.__class__.__module__:
                agent_type = "Business"
            
            # Get tool count
            tool_count = 0
            if hasattr(agent, 'tool_manager') and agent.tool_manager:
                tool_count = len(agent.tool_manager.tools)
            elif hasattr(agent, 'tools') and agent.tools:
                tool_count = len(agent.tools)
            
            agent_table.add_row(
                agent.name,
                agent_type,
                agent.description[:47] + "..." if len(agent.description) > 50 else agent.description,
                str(tool_count) if tool_count > 0 else "N/A"
            )
        
        console.print(agent_table)
        console.print()
        
        # Show summary
        summary_panel = Panel(
            f"[bold green]🎯 Server Ready![/bold green]\n\n"
            f"[bold blue]Total Agents:[/bold blue] {len(agents)}\n"
            f"[bold cyan]Core Agents:[/bold cyan] {len(agents) - len(mcp_agents)}\n"
            f"[bold yellow]MCP Agents:[/bold yellow] {len(mcp_agents)}\n\n"
            f"[bold magenta]Access URL:[/bold magenta] http://{host}:{port}\n"
            f"[bold magenta]Agent Card:[/bold magenta] http://{host}:{port}/.well-known/agent.json\n\n"
            f"[dim]Press Ctrl+C to stop the server[/dim]",
            title="🚀 Tron A2A Server",
            style="green"
        )
        console.print(summary_panel)
        
        # Start the server
        uvicorn.run(server.build(), host=host, port=port, log_level="info")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(Panel(
            f"[bold red]Error starting server:[/bold red] {str(e)}",
            title="❌ Error",
            style="red"
        ))
    finally:
        # Cleanup MCP agents if they were loaded
        if include_mcp and 'manager' in locals():
            try:
                await manager.cleanup()
                console.print("[dim]MCP agents cleaned up[/dim]")
            except Exception:
                pass


@click.group()
def db():
    """Database management commands."""
    pass

@db.command()
async def init():
    """Initialize the database and create tables."""
    from tron_ai.database.manager import DatabaseManager
    from tron_ai.database.config import DatabaseConfig
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
    from tron_ai.database.manager import DatabaseManager
    from tron_ai.database.config import DatabaseConfig
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
    from tron_ai.database.manager import DatabaseManager
    from tron_ai.database.config import DatabaseConfig
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
    from tron_ai.database.manager import DatabaseManager
    from tron_ai.database.config import DatabaseConfig
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

@cli.command()
@click.argument("message", required=False, default="Hello, what can you help me with?")
@click.option("--host", default="127.0.0.1", help="A2A server host")
@click.option("--port", default=8000, help="A2A server port")
@click.option("--timeout", default=30, help="Request timeout in seconds")
async def test_a2a_server(message: str, host: str, port: int, timeout: int):
    """Test the A2A server by sending a message and displaying the response."""
    import asyncio
    import httpx
    from uuid import uuid4
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from a2a.client import A2ACardResolver, A2AClient
    from a2a.types import MessageSendParams, SendMessageRequest
    
    console = Console()
    
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            
            # Step 1: Test server connectivity
            task = progress.add_task("🔗 Connecting to server...", total=None)
            
            async with httpx.AsyncClient(timeout=timeout) as httpx_client:
                try:
                    # Test basic connectivity
                    response = await httpx_client.get(f"{base_url}/")
                    progress.update(task, description="✅ Server is reachable")
                except Exception as e:
                    console.print(Panel(
                        f"[bold red]❌ Cannot connect to server:[/bold red] {str(e)}\n\n"
                        f"Make sure the A2A server is running:\n"
                        f"[cyan]tron-ai start-a2a-server --host {host} --port {port}[/cyan]",
                        title="Connection Error",
                        style="red"
                    ))
                    return
                
                # Step 2: Get agent card
                progress.update(task, description="📋 Fetching agent card...")
                
                try:
                    resolver = A2ACardResolver(
                        httpx_client=httpx_client,
                        base_url=base_url,
                    )
                    
                    public_card = await resolver.get_agent_card()
                    progress.update(task, description="✅ Agent card retrieved")
                    
                    # Display agent info
                    console.print(Panel(
                        f"[bold green]Agent Name:[/bold green] {public_card.name}\n"
                        f"[bold blue]Description:[/bold blue] {public_card.description}\n"
                        f"[bold yellow]Version:[/bold yellow] {public_card.version}",
                        title="🤖 Agent Information",
                        style="green"
                    ))
                    
                except Exception as e:
                    console.print(Panel(
                        f"[bold red]❌ Failed to get agent card:[/bold red] {str(e)}",
                        title="Agent Card Error",
                        style="red"
                    ))
                    return
                
                # Step 3: Create client and send message
                progress.update(task, description="💬 Sending message...")
                
                try:
                    client = A2AClient(
                        httpx_client=httpx_client, 
                        agent_card=public_card
                    )

                    send_message_payload = {
                        'message': {
                            'role': 'user',
                            'parts': [
                                {'kind': 'text', 'text': message}
                            ],
                            'messageId': uuid4().hex,
                        },
                    }
                    
                    request = SendMessageRequest(
                        id=str(uuid4()), 
                        params=MessageSendParams(**send_message_payload)
                    )
                    
                    response = await client.send_message(request)
                    progress.update(task, description="✅ Message sent, processing response...")
                    
                    # Extract and display response with comprehensive handling
                    response_displayed = False
                    response_success = False
                    
                    try:
                        console.print("\n")
                        
                        # Handle different A2A response structures
                        if hasattr(response, 'root') and response.root:
                            root = response.root
                            
                            # Check for result structure
                            if hasattr(root, 'result') and root.result:
                                result = root.result
                                
                                # Handle status with message
                                if hasattr(result, 'status') and result.status:
                                    status = result.status
                                    
                                    if hasattr(status, 'message') and status.message:
                                        message = status.message
                                        
                                        # Extract text from message parts
                                        if hasattr(message, 'parts') and message.parts:
                                            for part in message.parts:
                                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                                    response_text = part.root.text
                                                elif hasattr(part, 'text'):
                                                    response_text = part.text
                                                else:
                                                    continue
                                                
                                                console.print(Panel(
                                                    Markdown(response_text),
                                                    title="🤖 Agent Response",
                                                    style="green"
                                                ))
                                                response_displayed = True
                                                response_success = True
                                                break
                                    
                                    # Handle task updates or other status info
                                    if hasattr(status, 'tasks') and status.tasks:
                                        console.print(Panel(
                                            f"[bold cyan]Task Updates:[/bold cyan]\n{status.tasks}",
                                            title="📋 Task Status",
                                            style="cyan"
                                        ))
                                        response_displayed = True
                                        response_success = True
                                
                                # Handle direct result content
                                if hasattr(result, 'content') and result.content:
                                    console.print(Panel(
                                        Markdown(str(result.content)),
                                        title="🤖 Agent Result",
                                        style="green"
                                    ))
                                    response_displayed = True
                                    response_success = True
                                
                                # Handle task result structure
                                if hasattr(result, 'task') and result.task:
                                    task = result.task
                                    task_info = []
                                    
                                    if hasattr(task, 'status'):
                                        task_info.append(f"**Status:** {task.status}")
                                    if hasattr(task, 'result'):
                                        task_info.append(f"**Result:** {task.result}")
                                    if hasattr(task, 'error'):
                                        task_info.append(f"**Error:** {task.error}")
                                    
                                    if task_info:
                                        console.print(Panel(
                                            Markdown('\n'.join(task_info)),
                                            title="📋 Task Details",
                                            style="yellow"
                                        ))
                                        response_displayed = True
                                        response_success = True
                        
                        # If we still haven't displayed anything, try to extract any text content
                        if not response_displayed:
                            # Try to convert response to string and look for meaningful content
                            response_str = str(response)
                            if len(response_str) > 50:  # Avoid showing tiny responses
                                console.print(Panel(
                                    f"[dim]Raw Response Structure:[/dim]\n{response_str[:1000]}{'...' if len(response_str) > 1000 else ''}",
                                    title="🔍 Debug Response",
                                    style="dim"
                                ))
                                response_displayed = True
                        
                        if not response_displayed:
                            console.print(Panel(
                                "[yellow]⚠️  No displayable content in response[/yellow]",
                                title="⚠️ Empty Response",
                                style="yellow"
                            ))
                            
                            # Show response attributes for debugging
                            if hasattr(response, '__dict__'):
                                attrs = [f"- {k}: {type(v).__name__}" for k, v in response.__dict__.items()]
                                console.print(Panel(
                                    '\n'.join(attrs),
                                    title="🔧 Response Attributes",
                                    style="dim"
                                ))
                        
                        # Show success/failure summary
                        if response_success:
                            console.print(Panel(
                                "[bold green]✅ Test completed successfully![/bold green]\n\n"
                                "The A2A server is working properly and can process requests.",
                                title="✅ Test Results",
                                style="green"
                            ))
                        else:
                            console.print(Panel(
                                "[bold yellow]⚠️  Test completed with warnings[/bold yellow]\n\n"
                                "The server responded but the response format was unexpected.",
                                title="⚠️ Test Results",
                                style="yellow"
                            ))
                            
                    except Exception as parse_error:
                        console.print(Panel(
                            f"[bold red]Error parsing response:[/bold red] {str(parse_error)}\n\n"
                            f"[dim]Raw response:[/dim] {response}",
                            title="❌ Parse Error",
                            style="red"
                        ))
                        
                except Exception as e:
                    console.print(Panel(
                        f"[bold red]❌ Failed to send message:[/bold red] {str(e)}",
                        title="Message Error",
                        style="red"
                    ))
                    return
    
    except Exception as e:
        console.print(Panel(
            f"[bold red]❌ Test failed:[/bold red] {str(e)}",
            title="Test Error",
            style="red"
        ))


@cli.command()
@click.option("--host", default="127.0.0.1", help="A2A server host")
@click.option("--port", default=8000, help="A2A server port")
async def test_a2a_interactive(host: str, port: int):
    """Start an interactive session with the A2A server."""
    import asyncio
    import httpx
    from uuid import uuid4
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.prompt import Prompt as RichPrompt
    from a2a.client import A2ACardResolver, A2AClient
    from a2a.types import MessageSendParams, SendMessageRequest
    
    console = Console()
    base_url = f'http://{host}:{port}'
    
    console.print(Panel(
        f"[bold cyan]🚀 Interactive A2A Client[/bold cyan]\n"
        f"[green]Server:[/green] {base_url}\n"
        f"[dim]Type 'quit' or 'exit' to stop[/dim]",
        title="Interactive Session",
        style="cyan"
    ))
    
    try:
        async with httpx.AsyncClient(timeout=60) as httpx_client:
            # Initialize client
            try:
                resolver = A2ACardResolver(
                    httpx_client=httpx_client,
                    base_url=base_url,
                )
                
                public_card = await resolver.get_agent_card()
                client = A2AClient(
                    httpx_client=httpx_client, 
                    agent_card=public_card
                )
                
                console.print(Panel(
                    f"[bold green]Connected to:[/bold green] {public_card.name}\n"
                    f"[green]Description:[/green] {public_card.description}",
                    title="🤖 Connected",
                    style="green"
                ))
                
            except Exception as e:
                console.print(Panel(
                    f"[bold red]❌ Cannot connect:[/bold red] {str(e)}\n\n"
                    f"Make sure the server is running:\n"
                    f"[cyan]tron-ai start-a2a-server --host {host} --port {port}[/cyan]",
                    title="Connection Error",
                    style="red"
                ))
                return
            
            # Interactive loop
            while True:
                try:
                    user_input = RichPrompt.ask("\n[bold green]You[/bold green]")
                    
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        console.print(Panel(
                            "[bold yellow]👋 Goodbye![/bold yellow]",
                            style="yellow"
                        ))
                        break
                    
                    # Send message
                    with console.status("[bold blue]🤔 Agent is thinking...[/bold blue]"):
                        send_message_payload = {
                            'message': {
                                'role': 'user',
                                'parts': [
                                    {'kind': 'text', 'text': user_input}
                                ],
                                'messageId': uuid4().hex,
                            },
                        }
                        
                        request = SendMessageRequest(
                            id=str(uuid4()), 
                            params=MessageSendParams(**send_message_payload)
                        )
                        
                        response = await client.send_message(request)
                    
                    # Display response with comprehensive handling
                    response_displayed = False
                    
                    try:
                        # Handle different A2A response structures
                        if hasattr(response, 'root') and response.root:
                            root = response.root
                            
                            # Check for result structure
                            if hasattr(root, 'result') and root.result:
                                result = root.result
                                
                                # Handle status with message
                                if hasattr(result, 'status') and result.status:
                                    status = result.status
                                    
                                    if hasattr(status, 'message') and status.message:
                                        message = status.message
                                        
                                        # Extract text from message parts
                                        if hasattr(message, 'parts') and message.parts:
                                            for part in message.parts:
                                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                                    response_text = part.root.text
                                                elif hasattr(part, 'text'):
                                                    response_text = part.text
                                                else:
                                                    continue
                                                
                                                console.print(Panel(
                                                    Markdown(response_text),
                                                    title="🤖 Agent Response",
                                                    style="blue"
                                                ))
                                                response_displayed = True
                                                break
                                    
                                    # Handle task updates or other status info
                                    if hasattr(status, 'tasks') and status.tasks:
                                        console.print(Panel(
                                            f"[bold cyan]Task Updates:[/bold cyan]\n{status.tasks}",
                                            title="📋 Task Status",
                                            style="cyan"
                                        ))
                                        response_displayed = True
                                
                                # Handle direct result content
                                if hasattr(result, 'content') and result.content:
                                    console.print(Panel(
                                        Markdown(str(result.content)),
                                        title="🤖 Agent Result",
                                        style="blue"
                                    ))
                                    response_displayed = True
                                
                                # Handle Task artifacts (might contain actual results)
                                if hasattr(result, 'artifacts') and result.artifacts:
                                    console.print(Panel(
                                        Markdown(f"**Task Artifacts:**\n{result.artifacts}"),
                                        title="📋 Task Artifacts",
                                        style="green"
                                    ))
                                    response_displayed = True
                                
                                # Handle Task history (might contain execution details)
                                if hasattr(result, 'history') and result.history:
                                    console.print(Panel(
                                        Markdown(f"**Task History:**\n{result.history}"),
                                        title="📋 Task History",
                                        style="cyan"
                                    ))
                                    response_displayed = True
                                
                                # Handle Task.result field (different from root.result)
                                if hasattr(result, 'result') and result.result:
                                    console.print(Panel(
                                        Markdown(f"**Task Result:**\n{result.result}"),
                                        title="📋 Task Result",
                                        style="blue"
                                    ))
                                    response_displayed = True
                                
                                # Handle task result structure (legacy)
                                if hasattr(result, 'task') and result.task:
                                    task = result.task
                                    task_info = []
                                    
                                    if hasattr(task, 'status'):
                                        task_info.append(f"**Status:** {task.status}")
                                    if hasattr(task, 'result'):
                                        task_info.append(f"**Result:** {task.result}")
                                    if hasattr(task, 'error'):
                                        task_info.append(f"**Error:** {task.error}")
                                    
                                    if task_info:
                                        console.print(Panel(
                                            Markdown('\n'.join(task_info)),
                                            title="📋 Task Details",
                                            style="yellow"
                                        ))
                                        response_displayed = True
                        
                        # If we still haven't displayed anything, try to extract any text content
                        if not response_displayed:
                            # Try to convert response to string and look for meaningful content
                            response_str = str(response)
                            if len(response_str) > 50:  # Avoid showing tiny responses
                                console.print(Panel(
                                    f"[dim]Raw Response Structure:[/dim]\n{response_str[:1000]}{'...' if len(response_str) > 1000 else ''}",
                                    title="🔍 Debug Response",
                                    style="dim"
                                ))
                                response_displayed = True
                        
                        if not response_displayed:
                            console.print("[yellow]⚠️  No displayable content in response[/yellow]")
                            
                            # Show response attributes for debugging
                            if hasattr(response, '__dict__'):
                                attrs = [f"- {k}: {type(v).__name__}" for k, v in response.__dict__.items()]
                                console.print(Panel(
                                    '\n'.join(attrs),
                                    title="🔧 Response Attributes",
                                    style="dim"
                                ))
                            
                    except Exception as parse_error:
                        console.print(Panel(
                            f"[bold red]Error parsing response:[/bold red] {str(parse_error)}\n\n"
                            f"[dim]Raw response:[/dim] {response}",
                            title="❌ Parse Error",
                            style="red"
                        ))
                        
                except KeyboardInterrupt:
                    console.print("\n[yellow]Session interrupted[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    
    except Exception as e:
        console.print(Panel(
            f"[bold red]❌ Session failed:[/bold red] {str(e)}",
            title="Session Error",
            style="red"
        ))

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
