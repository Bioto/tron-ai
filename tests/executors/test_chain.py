import pytest
from unittest.mock import Mock

from tron_intelligence.executors.base import ExecutorConfig
from tron_intelligence.executors.chain import ChainExecutor, Step
from tron_intelligence.utils.LLMClient import LLMClient
from tron_intelligence.prompts.models import Prompt, PromptDefaultResponse


class TestChainExecutor:
    """Tests for the ChainExecutor class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        client = Mock(spec=LLMClient)
        client.call.return_value = PromptDefaultResponse(response="test chain result")
        return client

    @pytest.fixture
    def mock_prompt(self):
        """Fixture for a mock Prompt."""
        prompt = Mock(spec=Prompt)
        prompt.build.return_value = "Test prompt"
        prompt.output_format = PromptDefaultResponse
        return prompt

    @pytest.fixture
    def executor_config(self, mock_client):
        """Fixture for a valid ExecutorConfig."""
        return ExecutorConfig(client=mock_client)

    @pytest.fixture
    def chain_executor(self, executor_config):
        """Fixture for a ChainExecutor instance."""
        return ChainExecutor(config=executor_config)

    def test_execute_chain(self, chain_executor, mock_client, mock_prompt):
        """Test that execute method properly chains steps."""
        # Arrange
        user_query = "Test query"
        steps = [Step(prompt=mock_prompt), Step(prompt=mock_prompt)]

        # Act
        result = chain_executor.execute(user_query=user_query, steps=steps)

        # Assert
        assert mock_client.call.call_count == 2
        assert isinstance(result, PromptDefaultResponse)
        assert result.response == "test chain result"

    def test_inheritance(self, chain_executor):
        """Test that ChainExecutor inherits from BaseExecutor."""
        from tron_intelligence.executors.base import BaseExecutor

        assert isinstance(chain_executor, BaseExecutor)
