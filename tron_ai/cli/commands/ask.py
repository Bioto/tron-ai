"""
Ask command for single-query interactions with agents.

This module provides a simple question-answer interface with agents.
"""

from typing import Optional

import asyncclick as click
from rich.console import Console

from tron_ai.cli.agent_factory import get_agent_factory
from tron_ai.cli.base import (
    CLIError,
    handle_cli_error,
    setup_cli_logging,
    validate_query_input,
    with_error_handling,
    with_validation
)


class AskCommandError(CLIError):
    """Raised when ask command encounters an error."""
    pass


@click.command(name='ask', help='Ask Tron AI a single question and get an immediate response.')
@click.argument("user_query", required=False)
@click.option("--agent", default="generic", help="Agent to use for the query")
@with_error_handling
@with_validation
async def ask(user_query: Optional[str], agent: str) -> None:
    """Ask Tron AI a single question and get an immediate response."""
    console = Console()
    setup_cli_logging()
    
    # Lazy imports to avoid initialization issues
    from adalflow import OpenAIClient
    from tron_ai.executors.agent import AgentExecutor
    from tron_ai.executors.completion import CompletionExecutor
    from tron_ai.models.config import LLMClientConfig
    from tron_ai.models.executors import ExecutorConfig
    from tron_ai.models.prompts import Prompt, PromptDefaultResponse
    from tron_ai.utils.llm.LLMClient import LLMClient
    
    # Validate input
    if not user_query:
        user_query = click.prompt("Please enter your question")
    
    validated_query = validate_query_input(user_query, "ask")
    
    # Create LLM client
    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o",
            json_output=True,
        ),
    )
    
    try:
        if agent == "generic":
            # Use completion executor for generic queries
            executor = CompletionExecutor(
                config=ExecutorConfig(
                    client=client,
                    prompt=Prompt(
                        text="You are a helpful AI assistant. Help the user with their query.",
                        output_format=PromptDefaultResponse
                    ),
                ),
            )
            response = await executor.execute(user_query=validated_query)
        else:
            # Use agent executor for specific agents
            agent_factory = get_agent_factory(console)
            agent_instance = agent_factory.create_agent(agent)
            
            executor = AgentExecutor(
                config=ExecutorConfig(
                    client=client,
                    logging=True,
                ),
            )
            response = await executor.execute(user_query=validated_query, agent=agent_instance)
        
        # Display response
        if hasattr(response, 'response') and response.response:
            console.print(response.response)
        elif hasattr(response, 'generated_output') and response.generated_output:
            console.print(response.generated_output)
        else:
            console.print("No response generated")
            
    except Exception as e:
        raise AskCommandError(f"Failed to process query: {e}") from e
