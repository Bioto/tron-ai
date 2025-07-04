import uvicorn
import httpx
from adalflow import OpenAIClient
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication

from tron_ai.executors.tasker.models import AgentManagerResults
from tron_ai.models.prompts import Prompt
from tron_ai.executors.agent import AgentExecutor
from tron_ai.models.agent import Agent
from tron_ai.executors.base import ExecutorConfig
from tron_ai.utils.llm.LLMClient import LLMClient, LLMClientConfig
from tron_ai.modules.a2a.executor import TronA2AExecutor


a2a_agent = Agent(
    name="Task Manager Agent",
    description="Analyzes user queries and breaks them down into logically grouped tasks, assigning operations to appropriate agents based on their capabilities",
    prompt=Prompt(
        text="You are a helpful assistant that analyzes user queries and breaks them down into logically grouped tasks, assigning operations to appropriate agents based on their capabilities.",
        output_format=AgentManagerResults
    ),
)

simple_agent = Agent(
    name="Color Picker Agent",
    description="An agent that returns hex color values based on user descriptions",
    prompt=Prompt(
        text="Return only the hex color value (e.g. #FF0000) that best matches the user's description. Do not include any additional text or explanation.",
    ),
)

config = ExecutorConfig(client=LLMClient(
    client=OpenAIClient(),
    config=LLMClientConfig(
        model_name="gpt-4o",
        json_output=True,
    ),
), logging=False)

executor = AgentExecutor(
    config=config,
    agents=[a2a_agent, simple_agent]
)

a2a_executor = TronA2AExecutor(
    agent=a2a_agent,
    executor=executor
)

httpx_client = httpx.AsyncClient()
request_handler = DefaultRequestHandler(
    agent_executor=a2a_executor,
    task_store=InMemoryTaskStore(),
    push_notifier=InMemoryPushNotifier(httpx_client),
)
server = A2AStarletteApplication(
    agent_card=a2a_agent.to_a2a_card(), http_handler=request_handler
)

if __name__ == "__main__":
    uvicorn.run(server.build(), host="0.0.0.0", port=8000)