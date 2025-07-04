import asyncclick as click
import asyncio

from tron_ai.models.config import LLMClientConfig
from tron_ai.utils.LLMClient import LLMClient
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from tron_ai.models.executors import ExecutorConfig
from tron_ai.executors.completion import CompletionExecutor

from adalflow import OpenAIClient

@click.group()
async def cli():
    """Command line interface for Tron AI"""
    pass


@cli.command()
@click.argument("user_query")
@click.option("--agent", default="generic", type=click.Choice(["generic", "tasker"]))
async def ask(user_query: str, agent: str) -> str:
    """Ask Tron AI a question"""

    # Initialize a basic prompt and client
    prompt = Prompt(
        text="You are a helpful AI assistant. Help the user with their query.",
        output_format=PromptDefaultResponse
    )
    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o",
            json_output=True,
        ),
    )
    
    executor = CompletionExecutor(
        config=ExecutorConfig(
            client=client,
            prompt=prompt,
        ),
    )
    response = await executor.execute(user_query=user_query)
    
    
    print(response.response)

def main():
    """Entry point that suppresses SystemExit traceback"""
    import sys
    
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
