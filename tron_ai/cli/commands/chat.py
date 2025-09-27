"""
Chat commands for interactive sessions with agents.

This module provides chat functionality with improved error handling,
input validation, and modular agent management.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import List, Optional

import asyncclick as click
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt as RichPrompt

from tron_ai.cli.agent_factory import get_agent_factory
from tron_ai.cli.base import (
    CLIError,
    ValidationError,
    handle_cli_error,
    setup_cli_logging,
    validate_query_input,
    with_error_handling,
    with_validation
)
from tron_ai.models.config import BaseXAICofig

from tron_ai.utils.memory.memory import AgentMemoryManager


class ChatSessionError(CLIError):
    """Raised when chat session encounters an error."""
    pass


class ChatSession:
    """
    Manages an interactive chat session with agents.
    
    Encapsulates chat state and provides clean separation of concerns.
    """
    
    def __init__(self, agent_name: str, mode: str = "regular", mcp_agent: Optional[str] = None):
        self.agent_name = agent_name
        self.mode = mode
        self.mcp_agent = mcp_agent
        self.console = Console()
        self.session_id = str(uuid.uuid4())
        self.db_manager: Optional[DatabaseManager] = None
        self.memory_manager: Optional[AgentMemoryManager] = None
        self.agent_factory = get_agent_factory(self.console)
        
    async def initialize(self) -> None:
        """Initialize the chat session."""
        setup_cli_logging()
        
        # Lazy imports to avoid initialization issues
        from tron_ai.database.config import DatabaseConfig
        from tron_ai.database.manager import DatabaseManager
        from tron_ai.models.config import BaseGroqConfig
        from tron_ai.utils.llm.LLMClient import get_llm_client_from_config
        
        # Initialize database
        db_config = DatabaseConfig()
        self.db_manager = DatabaseManager(db_config)
        await self.db_manager.initialize()
        
        # Initialize memory manager
        self.memory_manager = AgentMemoryManager()
        self.memory_manager.configure_memory(
            enabled=True,
            user_id="tron",
            search_limit=5,
            search_threshold=0.5
        )
        
        # Create LLM client
        self.client = get_llm_client_from_config(
            BaseXAICofig(model_name="grok-3"), 
            client_name="xai"
        )   
    
    def _get_primary_agent(self):
        """Get the primary agent for the session."""
        if self.mcp_agent:
            # Handle MCP agent (this would need async context)
            raise NotImplementedError("MCP agent support needs async refactoring")
        
        return self.agent_factory.create_agent(self.agent_name)
    
    def _get_swarm_agents(self) -> List:
        """Get all available agents for swarm mode."""
        all_agent_names = [
            "google", "android", "todoist", "notion", "ssh",
            "marketing_strategy", "sales", "customer_success",
            "product_management", "financial_planning", "ai_ethics",
            "content_creation", "community_relations"
        ]
        
        return self.agent_factory.create_agents_safely(all_agent_names)
    
    async def _create_conversation(self, agent_instance):
        """Create or get conversation in database."""
        conversation = await self.db_manager.get_conversation(self.session_id)
        if not conversation:
            conversation = await self.db_manager.create_conversation(
                session_id=self.session_id,
                user_id=None,
                agent_name=agent_instance.name,
                title=f"Chat with {agent_instance.name}",
                meta={"agent_type": self.agent_name, "mode": self.mode}
            )
        return conversation
    
    def _display_header(self, agent_instance) -> None:
        """Display chat session header."""
        header = Panel(
            f"[bold cyan]Tron AI Chat Session[/bold cyan]\n"
            f"[green]Agent:[/green] {agent_instance.name if self.mode == 'regular' else 'Swarm'}\n"
            f"[green]Mode:[/green] {self.mode}\n"
            f"[dim]Type 'exit', 'quit', or 'bye' to leave.[/dim]",
            style="bold magenta",
            expand=False
        )
        self.console.print(header)
    
    async def _process_user_input(self, user_input: str) -> str:
        """Process user input and add to conversation history."""
        # Validate input
        validated_input = validate_query_input(user_input, "chat")
        
        # Get conversation history for context
        conversation_history = await self.db_manager.get_conversation_history(
            self.session_id, max_messages=20
        )
        
        # Build context
        context = ""
        if conversation_history:
            context = f"## Conversation History\n{json.dumps(conversation_history, indent=2)}"
        
        full_query = f"{context}\nUser Input: {validated_input}"
        
        # Add user message to database
        await self.db_manager.add_message(
            session_id=self.session_id,
            role="user",
            content=validated_input,
            meta=None
        )
        
        return full_query.rstrip()
    
    async def _execute_agent_query(self, query: str, agent_instance, all_agents: List):
        """Execute query with appropriate executor."""
        from tron_ai.executors.agent import AgentExecutor
        from tron_ai.executors.swarm.executor import SwarmExecutor
        from tron_ai.executors.swarm.models import SwarmState
        from tron_ai.models.executors import ExecutorConfig
        
        if self.mode == "regular":
            # For TronAgent, populate memory_context
            prompt_kwargs = {}
            if agent_instance.name == "Tron":
                from tron_ai.agents.tron.tools import TronTools
                import json
                # Extract user input from query for memory search
                user_input_part = query.split("User Input:")[-1].strip() if "User Input:" in query else query
                memories_json = TronTools.query_memory(query=user_input_part)
                try:
                    memories = json.loads(memories_json)
                    memory_str = "## Relevant Memories\n\n"
                    if "results" in memories and memories["results"]:
                        for mem in memories["results"]:
                            memory_str += f"- {mem['memory']} (confidence: {mem.get('similarity', 0):.2f})\n\n"
                    else:
                        memory_str += "No relevant memories found yet. Our conversation history will help build this over time.\n"
                    prompt_kwargs = {"memory_context": memory_str}
                except json.JSONDecodeError:
                    prompt_kwargs = {"memory_context": "Memory query failed. Using conversation context."}
            
            executor = AgentExecutor(
                config=ExecutorConfig(
                    client=self.client,
                    logging=True,
                ),
            )
            return await executor.execute(user_query=query, agent=agent_instance, prompt_kwargs=prompt_kwargs)
        else:
            # Swarm mode
            swarm_state = SwarmState(agents=all_agents)
            swarm_executor = SwarmExecutor(
                state=swarm_state,
                config=ExecutorConfig(
                    client=self.client,
                    logging=True,
                ),
            )
            return await swarm_executor.execute(user_query=query)
    
    def _extract_response_content(self, response) -> str:
        """Extract displayable content from response."""
        if hasattr(response, "task_report") and callable(response.task_report):
            return response.task_report() or "No task report available"
        elif hasattr(response, "response") and response.response:
            return response.response
        elif hasattr(response, "generated_output") and response.generated_output:
            return response.generated_output
        else:
            return "No response generated"
    
    def _format_tool_calls(self, response) -> str:
        """Format tool calls for display."""
        if not (hasattr(response, 'tool_calls') and response.tool_calls):
            return ""
        
        tool_content = "\n\n### Diagnostic Message: Tools Used\n"
        for tc in response.tool_calls:
            tool_content += f"- **{tc['name']}**\n"
            
            if 'output' in tc:
                output_val = tc['output']
                if isinstance(output_val, (dict, list)):
                    try:
                        pretty_output = json.dumps(output_val, indent=2)
                        if len(pretty_output) > 500:
                            tool_content += "  Output (truncated):\n```json\n" + pretty_output[:500] + "...\n```\n"
                        else:
                            tool_content += "  Output:\n```json\n" + pretty_output + "\n```\n"
                    except Exception:
                        output_str = str(output_val)
                        if len(output_str) > 500:
                            tool_content += f"  Output (truncated): {output_str[:500]}...\n"
                        else:
                            tool_content += f"  Output: {output_str}\n"
                else:
                    output_str = str(output_val)
                    if len(output_str) > 500:
                        tool_content += f"  Output (truncated): {output_str[:500]}...\n"
                    else:
                        tool_content += f"  Output: {output_str}\n"
            
            if 'error' in tc:
                error_val = tc['error']
                if isinstance(error_val, (dict, list)):
                    try:
                        pretty_error = json.dumps(error_val, indent=2)
                        if len(pretty_error) > 500:
                            tool_content += "  Error (truncated):\n```json\n" + pretty_error[:500] + "...\n```\n"
                        else:
                            tool_content += "  Error:\n```json\n" + pretty_error + "\n```\n"
                    except Exception:
                        error_str = str(error_val)
                        if len(error_str) > 500:
                            tool_content += f"  Error (truncated): {error_str[:500]}...\n"
                        else:
                            tool_content += f"  Error: {error_str}\n"
                else:
                    error_str = str(error_val)
                    if len(error_str) > 500:
                        tool_content += f"  Error (truncated): {error_str[:500]}...\n"
                    else:
                        tool_content += f"  Error: {error_str}\n"
            
            tool_content += "\n"
        
        return tool_content
    
    def _format_diagnostics(self, response) -> str:
        """Format diagnostics for display."""
        if not (hasattr(response, 'diagnostics') and response.diagnostics):
            return ""
        
        diag_content = "\n\n### Response Diagnostics\n"
        diag_content += f"**Confidence Score:** {response.diagnostics.confidence:.2f}\n\n"
        diag_content += "**Thoughts:**\n"
        for thought in response.diagnostics.thoughts:
            diag_content += f"- {thought}\n"
        diag_content += "\n"
        
        return diag_content
    
    async def _save_agent_response(self, user_input: str, response, agent_name: str, execution_time_ms: int):
        """Save agent response to database."""
        # Extract response for database storage
        if hasattr(response, "task_report") and callable(response.task_report):
            agent_response_val = response.task_report()
        elif hasattr(response, "response") and response.response is not None:
            agent_response_val = response.response
        elif hasattr(response, "generated_output"):
            agent_response_val = response.generated_output
        else:
            agent_response_val = ""
        
        agent_response_str = (
            json.dumps(agent_response_val) 
            if isinstance(agent_response_val, dict) 
            else str(agent_response_val)
        )
        
        # Add agent session
        await self.db_manager.add_agent_session(
            session_id=self.session_id,
            agent_name=agent_name,
            user_query=user_input,
            agent_response=agent_response_str,
            tool_calls=getattr(response, 'tool_calls', None),
            execution_time_ms=execution_time_ms,
            success=True,
            meta=None
        )
        
        # Add assistant message
        md_content = self._extract_response_content(response)
        if isinstance(md_content, dict):
            md_content = json.dumps(md_content)
        else:
            md_content = str(md_content)
        
        await self.db_manager.add_message(
            session_id=self.session_id,
            role="assistant",
            content=md_content,
            agent_name=agent_name,
            tool_calls=getattr(response, 'tool_calls', None),
            meta=None
        )
        
        # Store interaction in vector memory
        if self.memory_manager:
            await self.memory_manager.store_interaction_memory(
                user_query=user_input,
                agent_response=response,
                agent_name=agent_name
            )
    
    async def run_interactive_session(self, initial_query: Optional[str] = None) -> None:
        """Run the main interactive chat loop."""
        try:
            # Get agents
            agent_instance = self._get_primary_agent()
            all_agents = self._get_swarm_agents()
            
            # Don't add TronAgent to swarm agents list - it's the orchestrator
            if agent_instance not in all_agents and type(agent_instance).__name__ != "TronAgent":
                all_agents.append(agent_instance)
                self.console.print(f"[green]✓[/green] Added requested agent: {agent_instance.name}")
            
            # Create conversation
            await self._create_conversation(agent_instance)
            
            # Display header
            self._display_header(agent_instance)
            
            # Main chat loop
            triggered = initial_query is None
            while True:
                try:
                    # Get user input
                    if triggered:
                        user_input = RichPrompt.ask("[bold green]You[/bold green]")
                    else:
                        user_input = initial_query
                        triggered = True
                    
                    # Check for exit commands
                    if user_input.strip().lower() in ["exit", "quit", "bye"]:
                        self.console.print(Panel("[bold yellow]Goodbye![/bold yellow]", style="yellow"))
                        break
                    
                    # Process input
                    full_query = await self._process_user_input(user_input)
                    
                    # Display user message
                    user_panel = Panel(
                        Align.left(f"[bold green]You:[/bold green] {user_input}"),
                        style="green",
                        title=f"{datetime.now():%H:%M:%S}",
                        border_style="green"
                    )
                    self.console.print(user_panel)
                    
                    # Execute with timing
                    start_time = time.time()
                    with self.console.status("[bold blue]Assistant is thinking...[/bold blue]", spinner="dots"):
                        response = await self._execute_agent_query(full_query, agent_instance, all_agents)
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Process response
                    agent_name = "swarm" if self.mode == "swarm" else agent_instance.name
                    
                    # Save to database
                    await self._save_agent_response(user_input, response, agent_name, execution_time_ms)
                    
                    # Display response
                    md_content = self._extract_response_content(response)
                    md_content = str(md_content) if md_content is not None else "No content available"
                    
                    # Add tool calls and diagnostics
                    md_content += self._format_tool_calls(response)
                    md_content += self._format_diagnostics(response)
                    
                    assistant_panel = Panel(
                        Markdown(md_content),
                        style="blue",
                        title=f"{agent_name} [{datetime.now():%H:%M:%S}]",
                        border_style="blue"
                    )
                    self.console.print(assistant_panel)
                    
                except KeyboardInterrupt:
                    self.console.print(Panel("\n[bold yellow]Goodbye![/bold yellow]", style="yellow"))
                    break
                except Exception as e:
                    handle_cli_error(ChatSessionError(f"Error during chat: {e}"), self.console)
                    
                    # Log error to database
                    if self.db_manager:
                        agent_name = "swarm" if self.mode == "swarm" else agent_instance.name
                        await self.db_manager.add_agent_session(
                            session_id=self.session_id,
                            agent_name=agent_name,
                            user_query=user_input if 'user_input' in locals() else "Unknown",
                            success=False,
                            error_message=str(e),
                            meta=None
                        )
                    
        finally:
            if self.db_manager:
                await self.db_manager.close()


@click.command(name='chat', help='Start an interactive chat session with an AI agent.')
@click.argument("user_query", required=False)
@click.option("--agent", default="tron", help="Agent to use for the chat session")
@click.option("--mcp-agent", default=None, help="Use a specific MCP agent by server name")
@click.option("--mode", default="regular", type=click.Choice(["regular", "swarm"]), 
              help="Execution mode (regular: single agent, swarm: multi-agent orchestration)")
@with_error_handling
@with_validation
async def chat(user_query: Optional[str], agent: str, mcp_agent: Optional[str], mode: str):
    """Start an interactive chat session with an AI agent."""
    session = ChatSession(agent_name=agent, mode=mode, mcp_agent=mcp_agent)
    await session.initialize()
    await session.run_interactive_session(initial_query=user_query)

 
 