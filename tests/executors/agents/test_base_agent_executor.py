import pytest
from unittest.mock import Mock, patch

from tron_ai.executors.base import ExecutorConfig
from tron_ai.executors.agents.base_executors import BaseAgentExecutor
from tron_ai.executors.agents.models.agent import Agent
from tron_ai.prompts.models import Prompt
from tron_ai.utils.LLMClient import LLMClient


class MockAgent(Agent):
    """Mock implementation of Agent for testing."""

    def __init__(self, name, description, supports_multiple_operations=True):
        super().__init__(
            name=name,
            description=description,
            prompt=Mock(spec=Prompt),
            supports_multiple_operations=supports_multiple_operations,
        )


class TestBaseAgentExecutor:
    """Tests for the BaseAgentExecutor class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        client = Mock(spec=LLMClient)
        return client

    @pytest.fixture
    def mock_agents(self):
        """Fixture for a list of mock agents."""
        return [
            MockAgent("TestAgent1", "Test agent 1 description"),
            MockAgent("TestAgent2", "Test agent 2 description"),
            MockAgent("TestAgent3", "Test agent 3 description", False),
        ]

    @pytest.fixture
    def executor_config(self, mock_client):
        """Fixture for a valid ExecutorConfig."""
        return ExecutorConfig(client=mock_client)

    @pytest.fixture
    def agent_executor(self, mock_agents, executor_config):
        """Fixture for a BaseAgentExecutor instance."""
        return BaseAgentExecutor(agents=mock_agents, config=executor_config)

    def test_initialization(self, agent_executor, mock_agents, executor_config):
        """Test that BaseAgentExecutor initializes with the given config and agents."""
        assert agent_executor._config is executor_config
        assert agent_executor.agents == mock_agents

    def test_refresh_agent_tools(self, agent_executor, mock_agents):
        """Test the _refresh_agent_tools method."""
        # Setup: Add a mock tool_manager to the first agent
        mock_agents[0].tool_manager = Mock()
        
        # Mock the tools method to be callable
        mock_agents[0].__class__.tools = Mock()

        # Act
        agent_executor._refresh_agent_tools()

        # Assert: Nothing to assert directly, but we can check if logger was called
        # This is just to ensure the method runs without error.
        # A more detailed test would require a more complex mock setup.

    @pytest.mark.asyncio
    async def test_execute_not_implemented(self, agent_executor):
        """Test that the base execute method raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await agent_executor.execute()
