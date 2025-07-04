# Standard library imports
from typing import Generic, List, TypeVar
import logging

# Local imports
from tron_ai.executors.base import BaseExecutor, ExecutorConfig
from tron_ai.executors.agents.models.agent import Agent

R = TypeVar("R")

class BaseAgentExecutor(BaseExecutor, Generic[R]):
    """Base class for agent executors that provides core agent management functionality.

    This class serves as the foundation for all agent executors in the system. It handles
    agent initialization, tool management, and provides a common interface for execution.
    Subclasses must implement their own execution strategies (e.g., task-based, direct, etc.).

    Type Parameters:
        R: The return type of the execute method, which varies by executor implementation.

    Attributes:
        agents (List[Agent]): List of agents managed by this executor
        logger (logging.Logger): Logger instance for this executor
    """

    def __init__(self, agents: List[Agent], config: ExecutorConfig, *args, **kwargs) -> None:
        """Initialize the base agent executor.

        Args:
            agents: List of Agent instances to be managed by this executor
            config: Configuration object for the executor
            *args: Additional positional arguments passed to parent class
            **kwargs: Additional keyword arguments passed to parent class
        """
        super().__init__(config=config, *args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.agents = agents

    def _prepare_agents(self) -> None:
        """Prepare all agents for execution by refreshing their tools.

        This method ensures all agents have up-to-date tools before execution begins.
        It's called automatically before execution starts.
        """
        self._refresh_agent_tools()

    def _refresh_agent_tools(self) -> None:
        """Refresh tools for all agents that support dynamic tool refreshing.

        This method iterates through all agents and refreshes their tools if they
        support dynamic tool management. It logs the refresh operation for each agent.
        """
        for agent in self.agents:
            if hasattr(agent, "tools") and callable(getattr(agent.__class__, "tools", None)):
                self.logger.info(f"Refreshing tools for agent '{agent.name}'")
                agent.tool_manager

    async def execute(self, *args, **kwargs) -> R:
        """Execute the agent workflow.

        This is an abstract method that must be implemented by subclasses to define
        their specific execution strategy.

        Args:
            *args: Variable length argument list for execution parameters
            **kwargs: Arbitrary keyword arguments for execution parameters

        Returns:
            R: The result of execution, type varies by implementation

        Raises:
            NotImplementedError: Always raised as this is an abstract method
        """
        raise NotImplementedError("Subclasses must implement the execute method.")

# Note: ReportingAgentExecutor will need to be refactored to use TaskAgentExecutor for task-based reporting.
