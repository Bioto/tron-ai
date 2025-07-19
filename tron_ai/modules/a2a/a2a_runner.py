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
from tron_ai.modules.a2a.session_manager import A2ASessionManager
from tron_ai.database.manager import DatabaseManager
from tron_ai.database.config import DatabaseConfig


# Create agents
a2a_agent = Agent(
    name="Task Manager Agent",
    description="Analyzes user queries and breaks them down into logically grouped tasks, assigning operations to appropriate agents based on their capabilities",
    prompt=Prompt(
        text="You are a helpful assistant that analyzes user queries and breaks them down into logically grouped tasks, assigning operations to appropriate agents based on their capabilities.",
        output_format=SwarmResults
    ),
)

simple_agent = Agent(
    name="Color Picker Agent",
    description="An agent that returns hex color values based on user descriptions",
    prompt=Prompt(
        text="Return only the hex color value (e.g. #FF0000) that best matches the user's description. Do not include any additional text or explanation.",
    ),
)

# List of all agents available for A2A tasks
agents = [a2a_agent, simple_agent]

# Create executor config
config = ExecutorConfig(client=get_llm_client(json_output=True), logging=False)

# Create base executor
executor = AgentExecutor(
    config=config,
    agents=agents
)

# Create database manager and session manager for A2A session continuity
db_manager = DatabaseManager(DatabaseConfig())
session_manager = A2ASessionManager(db_manager=db_manager)

# Create A2A executor with session continuity support
a2a_executor = TronA2AExecutor(
    agent=a2a_agent,
    executor=executor,
    agents=agents,  # Pass the agents list for swarm execution
    session_manager=session_manager  # Enable session continuity
)

# Create HTTP components
httpx_client = httpx.AsyncClient()
request_handler = DefaultRequestHandler(
    agent_executor=a2a_executor,
    task_store=InMemoryTaskStore(),
    push_notifier=InMemoryPushNotifier(httpx_client),
)

# Create A2A server
server = A2AStarletteApplication(
    agent_card=a2a_agent.to_a2a_card(), 
    http_handler=request_handler
)

# Initialize database on startup
async def initialize_services():
    """Initialize database and other services."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        await session_manager.initialize()
        logger.info("A2A session manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize session manager: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize services
    asyncio.run(initialize_services())
    logger.info("Starting A2A server with session continuity support")
    
    # Start the server
    uvicorn.run(server.build(), host="0.0.0.0", port=8000)