import pytest
from unittest.mock import Mock

from tron_ai.executors.agents.models.agent import Agent, AgentExecutorResponse
from tron_ai.prompts.models import Prompt, ToolCall
from adalflow.core.tool_manager import ToolManager


class TestAgent:
    """Tests for the Agent class."""

    @pytest.fixture
    def mock_prompt(self):
        """Fixture for a mock Prompt."""
        return Mock(spec=Prompt)

    @pytest.fixture
    def mock_tool_manager(self):
        """Fixture for a mock ToolManager."""
        tool_manager = Mock(spec=ToolManager)
        mock_tool = Mock()
        mock_tool.definition.func_name = "test_tool"
        tool_manager.tools = [mock_tool]
        return tool_manager

    @pytest.fixture
    def basic_agent(self, mock_prompt):
        """Fixture for a basic Agent instance without tools."""
        return Agent(
            name="TestAgent",
            description="Test agent description",
            prompt=mock_prompt,
            supports_multiple_operations=True,
        )

    @pytest.fixture
    def agent_with_tools(self, mock_prompt, mock_tool_manager):
        """Fixture for an Agent instance with tools."""
        return Agent(
            name="ToolAgent",
            description="Agent with tools",
            prompt=mock_prompt,
            supports_multiple_operations=True,
            tool_manager=mock_tool_manager,
        )

    def test_initialization(self, basic_agent, mock_prompt):
        """Test that Agent initializes with the basic properties."""
        assert basic_agent.name == "TestAgent"
        assert basic_agent.description == "Test agent description"
        assert basic_agent.prompt is mock_prompt
        assert basic_agent.supports_multiple_operations is True
        assert basic_agent.tool_manager is None

    def test_initialization_with_tools(
        self, agent_with_tools, mock_prompt, mock_tool_manager
    ):
        """Test that Agent initializes with tools."""
        assert agent_with_tools.name == "ToolAgent"
        assert agent_with_tools.description == "Agent with tools"
        assert agent_with_tools.prompt is mock_prompt
        assert agent_with_tools.supports_multiple_operations is True
        assert agent_with_tools.tool_manager is mock_tool_manager

    def test_full_description_without_tools(self, basic_agent):
        """Test the full_description property without tools."""
        expected = "TestAgent: Test agent description"
        assert basic_agent.full_description == expected

    def test_full_description_with_tools(self, agent_with_tools):
        """Test the full_description property with tools."""
        expected = "ToolAgent: Agent with tools\n\nTools: test_tool"
        assert agent_with_tools.full_description == expected


class TestToolCall:
    """Tests for the ToolCall class."""

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        tool_call = ToolCall(func_name="test_tool", args=[], kwargs={})
        assert tool_call.func_name == "test_tool"
        assert tool_call.args == []
        assert tool_call.kwargs == {}

    def test_initialization_with_args(self):
        """Test initialization with args."""
        tool_call = ToolCall(func_name="test_tool", args=["arg1", "arg2"], kwargs={})
        assert tool_call.func_name == "test_tool"
        assert tool_call.args == ["arg1", "arg2"]
        assert tool_call.kwargs == {}

    def test_initialization_with_kwargs(self):
        """Test initialization with kwargs."""
        tool_call = ToolCall(
            func_name="test_tool", args=[], kwargs={"key1": "value1", "key2": "value2"}
        )
        assert tool_call.func_name == "test_tool"
        assert tool_call.args == []
        assert tool_call.kwargs == {"key1": "value1", "key2": "value2"}

    def test_initialization_with_args_and_kwargs(self):
        """Test initialization with both args and kwargs."""
        tool_call = ToolCall(
            func_name="test_tool", args=["arg1"], kwargs={"key1": "value1"}
        )
        assert tool_call.func_name == "test_tool"
        assert tool_call.args == ["arg1"]
        assert tool_call.kwargs == {"key1": "value1"}


class TestAgentExecutorResponse:
    """Tests for the AgentExecutorResponse class."""

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        response = AgentExecutorResponse(response="Test response", agent_name="TestAgent")
        assert response.response == "Test response"
        assert response.agent_name == "TestAgent"
        assert response.tool_calls == []

    def test_initialization_with_tool_calls(self):
        """Test initialization with tool calls."""
        tool_calls = [
            ToolCall(func_name="tool1", args=["arg1"], kwargs={}),
            ToolCall(func_name="tool2", args=[], kwargs={"key": "value"}),
        ]

        response = AgentExecutorResponse(
            response="Test response with tools",
            agent_name="TestAgent",
            tool_calls=tool_calls
        )

        assert response.response == "Test response with tools"
        assert response.agent_name == "TestAgent"
        assert len(response.tool_calls) == 2
        assert response.tool_calls[0].func_name == "tool1"
        assert response.tool_calls[1].func_name == "tool2"
