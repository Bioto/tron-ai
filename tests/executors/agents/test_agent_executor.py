import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import dataclass

from tron_ai.executors.base import ExecutorConfig
from tron_ai.executors.agents.executor import AgentExecutor
from tron_ai.executors.agents.base_executors import (
    BaseAgentExecutor,
)
from tron_ai.executors.agents.models.agent import Agent, AgentExecutorResponse, AgentExecutorResults
from tron_ai.prompts.models import Prompt, PromptDiagnostics, PromptDefaultResponse
from tron_ai.modules.tasks import Task
from tron_ai.utils.LLMClient import LLMClient


@dataclass
class TaskResult:
    """Test representation of a task result."""

    success: bool
    message: str
    response: str
    confidence: float


class MockAgent(Agent):
    """Mock implementation of Agent for testing."""

    def __init__(self, name, description, supports_multiple_operations=True):
        mock_prompt = Mock(spec=Prompt)
        mock_prompt.output_format = PromptDefaultResponse
        super().__init__(
            name=name,
            description=description,
            prompt=mock_prompt,
            supports_multiple_operations=supports_multiple_operations,
        )

    async def execute(self, operations, context=None):
        return TaskResult(
            success=True,
            message="Executed successfully",
            response=f"Executed {len(operations)} operations using {self.name}",
            confidence=0.9,
        )


class TestAgentExecutor:
    """Tests for the AgentExecutor class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        client_mock = Mock(spec=LLMClient)
        client_mock.fcall = AsyncMock(
            return_value=AgentExecutorResponse(
                agent_name="TestAgent1",
                response="Response from agent",
                diagnostics=PromptDiagnostics(thoughts=[], confidence=1.0),
            )
        )
        return client_mock

    @pytest.fixture
    def mock_agents(self):
        """Fixture for a list of mock agents."""
        return [
            MockAgent("TestAgent1", "Test agent 1 description"),
            MockAgent("TestAgent2", "Test agent 2 description"),
        ]

    @pytest.fixture
    def executor_config(self, mock_client):
        """Fixture for a valid ExecutorConfig."""
        return ExecutorConfig(client=mock_client)

    @pytest.fixture
    def agent_executor(self, mock_agents, executor_config):
        """Fixture for an AgentExecutor instance."""
        return AgentExecutor(agents=mock_agents, config=executor_config)

    def test_inheritance(self, agent_executor):
        """Test that AgentExecutor inherits from BaseAgentExecutor."""
        assert isinstance(agent_executor, BaseAgentExecutor)

    def test_initialization(self, agent_executor, mock_agents, executor_config):
        """Test that AgentExecutor initializes correctly."""
        assert agent_executor._config is executor_config
        assert agent_executor.agents == mock_agents

    @pytest.mark.asyncio
    @patch("asyncio.gather")
    async def test_execute(self, mock_gather, agent_executor, mock_agents):
        """Test the execute method of AgentExecutor."""
        # Setup
        user_query = "Test user query"
        
        mock_responses = [
            AgentExecutorResponse(
                agent_name=agent.name,
                response=f"Response from {agent.name}",
                diagnostics=PromptDiagnostics(thoughts=[], confidence=1.0)
            ) for agent in mock_agents
        ]
        mock_gather.return_value = mock_responses
        agent_executor.execute_agents = AsyncMock(return_value=mock_responses)

        # Execute
        result = await agent_executor.execute(user_query)

        # Verify
        assert isinstance(result, AgentExecutorResults)
        assert len(result.results) == len(mock_agents)
        agent_executor.execute_agents.assert_called_once_with(user_query, {agent.name: agent for agent in mock_agents})

    @pytest.mark.asyncio
    async def test_execute_agents(self, agent_executor, mock_agents, mock_client):
        """Test the execute_agents method."""
        user_query = "Test query"
        agents_dict = {agent.name: agent for agent in mock_agents}

        # Execute
        results = await agent_executor.execute_agents(user_query, agents_dict)

        # Verify
        assert len(results) == len(mock_agents)
        assert mock_client.fcall.call_count == len(mock_agents)
        for agent in mock_agents:
            mock_client.fcall.assert_any_call(
                user_query=user_query,
                system_prompt=agent.prompt,
                tool_manager=agent.tool_manager,
                prompt_kwargs={},
                output_data_class=agent.prompt.output_format
            )
