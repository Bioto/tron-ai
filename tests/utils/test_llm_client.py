"""
Tests for the LLMClient module.

Note: This file tests only LLMClient. For MCP agent pool/manager tests, see tests/executors/agents/builtin/test_mcp_agent_manager.py.
"""

import pytest
from unittest.mock import Mock, patch
import json
import orjson
from pydantic import BaseModel

from tron_ai.utils.LLMClient import LLMClient, LLMClientConfig, BASE_PROMPT
from tron_ai.models.prompts import Prompt
from tron_ai.constants import LLM_DEFAULT_TEMPERATURE
from adalflow.core.types import FunctionOutput


class MockResponseModel(BaseModel):
    """Mock response model for testing."""

    response: str


class _TestResponse(BaseModel):
    """Test response model for tool manager tests."""

    response: str
    tool_calls: list = []


class TestLLMClient:
    """Test suite for LLMClient."""

    @pytest.fixture
    def mock_model_client(self):
        """Create a mock model client."""
        return Mock()

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return LLMClientConfig(model_name="test-model", json_output=True, logging=True)

    @pytest.fixture
    def client(self, mock_model_client, config):
        """Create a test LLM client."""
        return LLMClient(client=mock_model_client, config=config)

    def test_initialization(self, client, mock_model_client, config):
        """Test client initialization."""
        assert client._client == mock_model_client
        assert client._config == config
        assert client.api_client == mock_model_client
        assert client.model == "test-model"

    def test_logging_enabled(self, mock_model_client, caplog):
        """Test logging when enabled."""
        from unittest.mock import patch

        config = LLMClientConfig(
            model_name="test-model", json_output=True, logging=True
        )
        client = LLMClient(client=mock_model_client, config=config)

        # Mock the logger.info method to verify it's called
        with patch("tron_ai.utils.LLMClient.logger.info") as mock_info:
            client._log("Test message")
            mock_info.assert_called_once_with("[LLMClient] Test message")

    def test_logging_disabled(self, mock_model_client):
        """Test logging when disabled."""
        config = LLMClientConfig(
            model_name="test-model", json_output=True, logging=False
        )
        client = LLMClient(client=mock_model_client, config=config)

        with patch("tron_ai.utils.LLMClient.logger") as mock_logger:
            client._log("Test message")
            mock_logger.info.assert_not_called()

    @patch("tron_ai.utils.LLMClient.Generator")
    def test_build_generator_with_json(self, mock_generator_class, client):
        """Test building generator with JSON output."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        client._build_generator()

        mock_generator_class.assert_called_once()
        call_kwargs = mock_generator_class.call_args[1]
        assert call_kwargs["template"] == BASE_PROMPT
        assert call_kwargs["model_client"] == client._client
        assert call_kwargs["model_kwargs"]["model"] == "test-model"
        assert call_kwargs["model_kwargs"]["temperature"] == LLM_DEFAULT_TEMPERATURE
        assert call_kwargs["model_kwargs"]["response_format"] == {"type": "json_object"}

    @patch("tron_ai.utils.LLMClient.Generator")
    def test_build_generator_without_json(
        self, mock_generator_class, mock_model_client
    ):
        """Test building generator without JSON output."""
        config = LLMClientConfig(
            model_name="test-model", json_output=False, logging=False
        )
        client = LLMClient(client=mock_model_client, config=config)

        client._build_generator()

        call_kwargs = mock_generator_class.call_args[1]
        assert "response_format" not in call_kwargs["model_kwargs"]

    @patch("tron_ai.utils.LLMClient.Generator")
    def test_call_success(self, mock_generator_class, client):
        """Test successful call method."""
        # Setup mocks
        mock_generator = Mock()
        mock_results = Mock()
        mock_results.raw_response = '{"response": "Test response"}'
        mock_generator.return_value = mock_results
        mock_generator_class.return_value = mock_generator

        # Create prompt
        prompt = Prompt(text="Test prompt", output_format=MockResponseModel)

        # Execute
        response = client.call("Test query", prompt)

        # Assertions
        assert isinstance(response, MockResponseModel)
        assert response.response == "Test response"
        mock_generator.assert_called_once()

    @patch("tron_ai.utils.LLMClient.Generator")
    def test_call_parse_error(self, mock_generator_class, client):
        """Test call method with parse error."""
        # Setup mocks
        mock_generator = Mock()
        mock_results = Mock()
        mock_results.raw_response = "invalid json"
        mock_generator.return_value = mock_results
        mock_generator_class.return_value = mock_generator

        # Create prompt
        prompt = Prompt(text="Test prompt", output_format=MockResponseModel)

        # Execute and expect error
        with pytest.raises(Exception):
            client.call("Test query", prompt)

    def test_format_query_with_results(self, client):
        """Test formatting query with tool results."""
        # Test with empty results
        result = client._format_query_with_results("Query", [])
        assert result == "Query"

        # Test with results - create proper mock objects
        mock_result1 = Mock()
        mock_result1.name = "tool1"
        mock_result1.output = "output1"

        mock_result2 = Mock()
        mock_result2.name = "tool2"
        mock_result2.output = "output2"

        mock_results = [mock_result1, mock_result2]
        result = client._format_query_with_results("Query", mock_results)
        assert "Query" in result
        assert "Tool Calls Results:" in result
        assert "tool1: output1" in result
        assert "tool2: output2" in result

    def test_execute_tool_calls_empty(self, client):
        """Test executing empty tool calls."""
        mock_tool_manager = Mock()
        result = client._execute_tool_calls([], mock_tool_manager)
        assert result == []
        mock_tool_manager.execute_func.assert_not_called()

    @patch("tron_ai.utils.LLMClient.Function")
    def test_execute_tool_calls_with_tools(self, mock_function_class, client):
        """Test executing tool calls."""
        # Setup mocks
        mock_tool_manager = Mock()
        mock_tool = Mock()
        mock_function_class.from_dict.return_value = mock_tool
        mock_tool_manager.execute_func.return_value = "tool_result"

        # Execute
        tool_calls = [{"name": "test_tool", "args": {}}]
        results = client._execute_tool_calls(tool_calls, mock_tool_manager)

        # Assertions
        assert len(results) == 1
        assert results[0] == "tool_result"
        mock_function_class.from_dict.assert_called_once_with(tool_calls[0])
        mock_tool_manager.execute_func.assert_called_once_with(mock_tool)

    def test_add_unique_results(self, client):
        """Test adding unique results."""
        # Create mock results with proper spec
        existing = [Mock(spec=["name", "output"])]
        existing[0].name = "tool1"
        existing[0].output = "output1"

        new_result1 = Mock(spec=["name", "output"])
        new_result1.name = "tool1"
        new_result1.output = "output1"

        new_result2 = Mock(spec=["name", "output"])
        new_result2.name = "tool2"
        new_result2.output = "output2"

        new_results = [new_result1, new_result2]

        # Execute
        client._add_unique_results(existing, new_results)

        # Assertions
        assert len(existing) == 2
        # First should be the original
        assert existing[0].name == "tool1"
        assert existing[0].output == "output1"
        # Second should be the new unique one
        assert existing[1].name == "tool2"
        assert existing[1].output == "output2"

    def test_should_continue_iteration(self, client):
        """Test iteration continuation logic."""
        # Test case: has tool calls, should continue
        dataset = {"tool_calls": [{"name": "tool"}]}
        response = Mock()
        assert client._should_continue_iteration(dataset, response, 0, 10)

        # Test case: no tool calls, no follow up, should stop
        dataset = {"tool_calls": []}
        response = Mock()
        assert not client._should_continue_iteration(dataset, response, 0, 10)

        # Test case: at max retries, should stop
        dataset = {"tool_calls": [{"name": "tool"}]}
        response = Mock()
        assert not client._should_continue_iteration(dataset, response, 9, 10)

    @pytest.mark.asyncio
    @patch("tron_ai.utils.LLMClient.Generator")
    async def test_execute_direct_call(self, mock_generator_class, client):
        """Test direct call execution."""
        # Setup mocks
        mock_generator = Mock()
        mock_results = Mock()
        mock_results.data = orjson.dumps({"response": "Direct response"})
        mock_generator.return_value = mock_results
        mock_generator_class.return_value = mock_generator

        # Create prompt
        prompt = Prompt(text="Test prompt", output_format=MockResponseModel)

        # Execute without tool results
        response = await client._execute_direct_call(
            mock_generator, prompt, "Query", []
        )

        # Assertions
        assert isinstance(response, MockResponseModel)
        assert response.response == "Direct response"

        # Execute with tool results
        tool_results = [FunctionOutput(name="tool", output={"result": "output"})]
        response = await client._execute_direct_call(
            mock_generator, prompt, "Query", tool_results
        )
        assert isinstance(response, MockResponseModel)
        assert response.response == "Direct response"

    def _setup_mock_generator(self, mock_generator_class, responses):
        """Helper to set up the mock generator with a sequence of responses."""
        mock_generator = Mock()
        mock_results = [Mock() for _ in responses]
        for i, data in enumerate(responses):
            mock_results[i].data = orjson.dumps(data)
        mock_generator.side_effect = mock_results
        mock_generator_class.return_value = mock_generator
        return mock_generator

    @pytest.mark.asyncio
    @patch("tron_ai.utils.LLMClient.Generator")
    @patch("tron_ai.utils.LLMClient.Function")
    async def test_fcall_with_tool_manager_multiple_iterations(
        self, mock_function_class, mock_generator_class, client
    ):
        """Test fcall with multiple tool iterations."""
        # First response: has tool calls
        response1_data = {
            "tool_calls": [{"name": "test_tool", "args": {}}],
            "response": "Tool call generated",
        }
        # Second response: no tool calls, but follow_up
        response2_data = {"tool_calls": [], "response": "Final Answer"}

        # Mocks
        mock_generator = self._setup_mock_generator(
            mock_generator_class, [response1_data, response2_data]
        )

        # Create prompt
        prompt = Prompt(text="Test prompt", output_format=_TestResponse)

        # Execute
        mock_tool_manager = Mock()
        mock_tool_manager.tools = [Mock()]  # has one tool
        mock_tool_manager.execute_func.return_value = FunctionOutput(
            name="test_tool", output="tool output"
        )
        response = await client.fcall("Query", prompt, tool_manager=mock_tool_manager)

        # Assertions
        assert isinstance(response, _TestResponse)
        assert response.response == "Final Answer"
        assert mock_generator.call_count == 2
        mock_function_class.from_dict.assert_called_once()

    @pytest.mark.asyncio
    @patch("tron_ai.utils.LLMClient.Generator")
    async def test_fcall_without_tool_manager(self, mock_generator_class, client):
        """Test fcall without tool manager."""
        # Setup mocks
        mock_generator = Mock()
        mock_results = Mock()
        mock_results.data = orjson.dumps({"response": "No tools response"})
        mock_generator.return_value = mock_results
        mock_generator_class.return_value = mock_generator

        # Create prompt
        prompt = Prompt(text="Test prompt", output_format=MockResponseModel)

        # Execute
        mock_tool_manager = Mock()
        mock_tool_manager.tools = []
        response = await client.fcall("Query", prompt, tool_manager=mock_tool_manager)

        # Assertions
        assert isinstance(response, MockResponseModel)
        assert response.response == "No tools response"

    def test_prepare_tool_prompt_kwargs(self, client):
        """Test preparing tool prompt kwargs."""
        mock_tool_manager = Mock()
        mock_tool_manager.yaml_definitions = "yaml_defs"
        mock_tool_manager.tools = ["tool1", "tool2"]

        kwargs = client._prepare_tool_prompt_kwargs(mock_tool_manager, _TestResponse)

        assert kwargs["tools"] == "yaml_defs"
        assert "_output_format_str" in kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
