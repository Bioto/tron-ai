# Standard library imports
from pydantic import BaseModel

# Local imports
from tron_ai.executors.base import Executor
from tron_ai.models.agent import Agent


class AgentExecutor(Executor):
    """Base class for agent executors that handle agent execution workflows.
    
    This abstract base class provides a common interface for executing agents
    with user queries. It delegates the actual execution to the underlying
    client's function call mechanism, passing through the agent's prompt and
    tool manager.
    
    Subclasses should implement specific execution strategies while maintaining
    compatibility with the base interface.
    """
    
    async def execute(self, user_query: str, agent: Agent, prompt_kwargs: dict = {}) -> BaseModel:
        """Execute an agent with the given user query.
        
        Args:
            user_query: The user's input query to process
            agent: The agent instance to execute
            prompt_kwargs: Additional keyword arguments to pass to the prompt
            
        Returns:
            BaseModel: The processed response from the agent execution
            
        Raises:
            ExecutionError: If the agent execution fails
        """
        return await self.client.fcall(
            user_query=user_query,
            system_prompt=agent.prompt,
            tool_manager=agent.tool_manager,
            prompt_kwargs=prompt_kwargs
        )
