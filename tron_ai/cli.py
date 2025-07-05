import asyncclick as click
from rich.console import Console
from rich.prompt import Prompt as RichPrompt

from tron_ai.agents.google.agent import GoogleAgent
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

# Suppress Pydantic deprecation warnings from ChromaDB
warnings.filterwarnings("ignore", category=DeprecationWarning, module="chromadb")


memory = Memory(config=MemoryConfig(
    history_db_path="tron_history.db",
    vector_store=VectorStoreConfig(
        provider="chroma",
        config={
            "collection_name": "tron_memory",
            "path": "tron_memory.db",
            
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
@click.option("--agent", default="generic", type=click.Choice(["generic", "tron", "google"]))
async def chat(agent: str):
    """Start an interactive chat session with the Tron agent."""
    console = Console()
    client = LLMClient(
        client=OpenAIClient(),
        config=LLMClientConfig(
            model_name="gpt-4o",
            json_output=True,
        ),
    )
    
    if agent == "google":
        agent = GoogleAgent()
    else:
        agent = TronAgent()
        
    executor = AgentExecutor(
        config=ExecutorConfig(
            client=client,
            logging=True,
        ),
    )
    conversation_history = []
    console.print("[bold cyan]Welcome to Tron AI chat! Type 'exit', 'quit', or 'bye' to leave.[/bold cyan]")
    while True:
        try:
            user_input = RichPrompt.ask("[bold green]You[/bold green]")
            
            if user_input.strip().lower() in ["exit", "quit", "bye"]:
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break
            
            # relevant_memory = memory.search(query=user_input, user_id="tron", limit=5, threshold=0.5)
            

            # Format conversation history as a bulleted list with headers
            context = ""
            if conversation_history:
                context = f"## Conversation History\n{json.dumps(conversation_history, indent=2)}"
                
            
            # if relevant_memory["results"]:
            #     memories_str = "## Retrieved Memories About the User\n" + "\n".join(
            #         f"- {entry['memory']}" for entry in relevant_memory["results"]
            #     )
            
            #     full_query = f"{context}\n\n{memories_str}\n"
            # else:
            full_query = f"{context}\n" 
                
            full_query += f"User Input: {user_input}"
            
            print("Full Query:")
            print(full_query)
            
            conversation_history.append(("User", user_input))
            response = await executor.execute(user_query=full_query.rstrip(), agent=agent)
          
            memory.add([{
                "role": message[0].lower(),
                "content": message[1]             
            } for message in conversation_history], user_id="tron")
            
            conversation_history.append(("Assistant", response.response))
            
            console.print(f"[bold blue]Assistant:[/bold blue] {response.response}")
            
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Goodbye![/bold yellow]")
            break


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
