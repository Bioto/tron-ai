# Third-party imports
import asyncio
import logging
import json

import asyncclick as click
from adalflow import OpenAIClient
from rich.console import Console
from rich.prompt import Prompt as RichPrompt

from tron_ai.models.agent import Agent
from tron_ai.executors.base import ExecutorConfig
from tron_ai.executors.completion import CompletionExecutor
from tron_ai.models.prompts import Prompt, PromptDefaultResponse

# Local imports
from tron_ai.config import setup_logging
from tron_ai.utils.llm.LLMClient import LLMClient, LLMClientConfig

from tron_ai.modules.mcp.manager import MCPAgentManager
from tron_ai.modules.tasks.models import Task

# Setup logging
setup_logging()
logger = logging.getLogger("tron_ai.cli")

# Initialize console for rich prompt only
console = Console()

search_agent = SearchAgent()

class FunctionOutput:
    def __init__(self, output: str):
        self.output = output


@click.group()
async def cli():
    """Command line interface for Tron AI"""
    pass


@cli.command()
@click.argument("query")
async def ask(query):
    """Ask Tron AI a question"""

    # Initialize a basic prompt and client
    prompt = Prompt(
        text="You are a helpful AI assistant.",
    )
    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o",
            json_output=True,
        ),
    )
    executor = CompletionExecutor(config=ExecutorConfig(client=client, prompt=prompt))

    # Get response from LLM
    response = await executor.execute(
        query, tool_manager=generate_memory_tool(), system_prompt=prompt
    )

    logger.setLevel(logging.INFO)
    # Print the interaction
    logger.info(f"You: {query}")
    logger.info(f"Assistant: {response.response}\n")


@cli.command()
@click.argument("query", default="Hello, Assistant!", required=False)
async def assistant(query):
    """Start an interactive chat session with Tron AI"""
    from tron_ai.executors.completion import CompletionExecutor
    from tron_ai.models.prompts import Prompt

    async def run_assistant(query="Hello, Assistant!"):
        # Initialize prompt and client
        Prompt(
            text=load_prompt_content("cli_assistant_prompt"),
        )
        client = LLMClient(
            client=OpenAIClient(),
            config=LLMClientConfig(
                model_name="gpt-4o", json_output=True, logging=False
            ),
        )
        executor = CompletionExecutor(
            config=ExecutorConfig(client=client, logging=True)
        )

        conversation_history = []

        # If initial query provided, process it
        if query:
            response = await executor.execute(
                query,
                tool_manager=generate_memory_tool(),
                system_prompt=Prompt(
                    text=load_prompt_content("cli_assistant_prompt"),
                    output_format=PromptDefaultResponse,
                ),
            )
            conversation_history.append((query, response.response))

            logger.info(f"You: {query}")
            logger.info(f"Assistant: {response.response}\n")

        # Start interactive loop
        while True:
            try:
                user_input = RichPrompt().ask(prompt="[bold red]Input[/bold red]")
                if user_input.lower() in ["exit", "quit", "bye"]:
                    logger.info("Goodbye!")
                    break

                # Append conversation history to query for context
                context = "\n".join(
                    [f"User: {q}\nAssistant: {a}" for q, a in conversation_history]
                )
                full_query = f"{context}\nUser: {user_input}"

                response = await executor.execute(
                    full_query,
                    tool_manager=generate_memory_tool(),
                    system_prompt=Prompt(
                        text=load_prompt_content("cli_assistant_prompt"),
                        output_format=PromptDefaultResponse,
                    ),
                )
                conversation_history.append((user_input, response.response))

                logger.info(f"Assistant: {response.response}\n")

            except (KeyboardInterrupt, EOFError):
                logger.info("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error during assistant execution: {e}")
                raise CLIError(
                    "Failed to process assistant request",
                    context={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )

    await run_assistant(query)


@cli.command()
async def chain():
    from tron_ai.executors.chain import ChainExecutor, Step
    from tron_ai.models.prompts import Prompt

    prompt = Prompt(
        text="You are a helpful AI assistant.",
    )
    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(model_name="gpt-4o", json_output=True, temperature=2),
    )

    executor = ChainExecutor(config=ExecutorConfig(client=client, prompt=prompt))

    results = executor.execute(
        "Write me a story about a dog who is a detective.",
        steps=[
            Step(
                prompt=Prompt(
                    text="Create a detailed character profile for our dog detective, including breed, personality traits, quirks, and detective style.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Design a love interest for the dog - another animal with their own career, personality, and how they first meet our detective.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Develop the setting - describe the city/town, the detective's office, and the general atmosphere of the story.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Create a complex crime with multiple suspects, red herrings, and interesting motives.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Develop a cast of supporting characters who will help or hinder the investigation.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Write the first act of the story, introducing the main characters and the crime.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Write the second act showing the investigation, red herrings, and developing relationship with the love interest.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Write the third act with the climax, resolution of both the crime and romance subplots.",
                )
            ),
            Step(
                prompt=Prompt(
                    text="Using all previous elements, compile everything into a cohesive story with rich details, dialogue, and descriptions.",
                )
            ),
        ],
    )

    logger.info(results.response)


@cli.command()
@click.argument("query")
@click.option(
    "--output", 
    "-o", 
    is_flag=True,
    help="Save the result to a markdown file in the output directory"
)
async def agent(query: str, output):
    """Execute a query using the MCP agent."""

    logger.info("Starting MCP Agent execution...")

    # Use LLMClient from cli.py scope or initialize a new one specific to this command
    llm_client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o", json_output=True, logging=True
        ),
    )

    # Create executor config
    config = ExecutorConfig(client=llm_client, logging=False)
        
    mcp_agent_manager = MCPAgentManager()
    await mcp_agent_manager.initialize()
    print(f"mcp_agent_manager: {len(mcp_agent_manager.agents)}")

    # Create the AgentExecutor with the MCP agent
    agent_executor = DelegateExecutor(
        config=config, state=DelegateState(
            agents=mcp_agent_manager.agents.values()
        )
    )

    # Create the CompletionExecutor for summarizing
    completion_executor = CompletionExecutor(config=config)

    logger.info(f"Executing agent query: {query}")
    # Execute the agent query
    delegate_state: DelegateState = await agent_executor.execute(user_query=query)
    task_list = {
        "tasks": []
    }
    for task in delegate_state.tasks:
        task_obj = Task.model_validate(task.model_dump())
        task_list["tasks"].append({
            "description": task_obj.description,
            "result": task_obj.result
        })
    
    logger.info("Generating final response...")
    # try:
    # Execute the completion query to summarize
    final_response = await asyncio.wait_for(
        completion_executor.execute(
            user_query=f'''
            Here are the tasks that were completed:
            {json.dumps(task_list)}
            ''',
            system_prompt=Prompt(
                text="Generate me a task summary of the tasks that were completed. Be sure to include all the details of the tasks in the summary. Make sure to answer the users query using the information from the tasks, Always include results from the tool calls in the response."
            ),
        ),
        timeout=TIMEOUT_COMPLETION,
    )

    logger.info("Final response generated:")
    logger.info(f"\t{final_response.response}")



@cli.command()
async def list_mcp_agents():
    """List all MCP agents and their status (test MCPAgentManager)."""
    manager = MCPAgentManager()
    await manager.initialize()
    agents = manager.agents
    if not agents:
        console.print("[bold red]No MCP agents found.[/bold red]")
        return
    console.print(f"[bold green]Loaded {len(agents)} MCP agents:[/bold green]")
    for name, agent in agents.items():
        status = "Initialized" if agent.mcp_client else "Not initialized"
        console.print(f"- [bold]{name}[/bold]: {status}")
    await manager.cleanup()


@cli.command()
async def test_agent_executor():
    """Test the agent executor."""
    # Use LLMClient from cli.py scope or initialize a new one specific to this command
    llm_client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o", json_output=True, logging=False,
        ),
    )

    agent = Agent(
        name="Test Agent",
        description="A test agent",
        prompt=Prompt(
            text="You are a test agent. You are tasked with testing the agent executor.",
            output_format=AgentManagerResults,
        )
    )

    # Create executor config
    config = ExecutorConfig(client=llm_client, logging=False)
    agent_executor = DelegateExecutor(config=config, state=DelegateState(agents=[agent]), client=llm_client)
    response = await agent_executor.execute(user_query="What is the capital of France?")
    console.print(response)

def main():
    """Entry point that suppresses SystemExit traceback"""
    import sys
    import os
    
    # Suppress the "Task exception was never retrieved" error by setting the asyncio logger
    # to a higher level before running the CLI
    import logging
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    
    # Also suppress stderr temporarily during the exit to catch any remaining output
    original_stderr = sys.stderr
    
    try:
        # Run the CLI
        cli(_anyio_backend="asyncio")
    except SystemExit as e:
        if e.code == 0:
            # For successful exits, suppress any remaining error output
            import io
            sys.stderr = io.StringIO()
        sys.exit(e.code)
    finally:
        # Restore stderr
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
