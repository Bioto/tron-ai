import pytest
from unittest.mock import AsyncMock, Mock

from tron_intelligence.executors.base import ExecutorConfig
from tron_intelligence.executors.completion import CompletionExecutor
from tron_intelligence.utils.LLMClient import LLMClient
from tron_intelligence.prompts.models import Prompt


class MockCompletionExecutor(CompletionExecutor):
    """Mock implementation of CompletionExecutor for testing"""

    async def execute(
        self,
        user_query: str,
        tool_manager,
        system_prompt,
        prompt_kwargs: dict = {},
    ):
        # Properly await the async call
        return await self.client.fcall(
            user_query=user_query,
            system_prompt=system_prompt,
            tool_manager=tool_manager,
            prompt_kwargs=prompt_kwargs,
        )


class TestCompletionExecutorIntegration:
    """Integration tests for CompletionExecutor with BaseExecutor."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient with fcall method."""
        client = Mock(spec=LLMClient)
        # Create a properly configured AsyncMock for fcall
        result = {"success": True}
        client.fcall = AsyncMock(return_value=result)
        return client

    @pytest.fixture
    def mock_prompt(self):
        """Fixture for a mock Prompt."""
        return Mock(spec=Prompt)

    @pytest.fixture
    def mock_tool_manager(self):
        """Fixture for a mock ToolManager."""
        manager = Mock()
        manager.tools = []
        return manager

    @pytest.fixture
    def executor_config(self, mock_client):
        """Fixture for a valid ExecutorConfig."""
        return ExecutorConfig(client=mock_client)

    @pytest.fixture
    def completion_executor(self, executor_config):
        """Fixture for a CompletionExecutor instance."""
        return MockCompletionExecutor(config=executor_config)

    @pytest.mark.asyncio
    async def test_execute_calls_client_fcall(
        self, completion_executor, mock_client, mock_prompt, mock_tool_manager
    ):
        """Test that execute method properly calls the client's fcall method."""
        # Arrange
        user_query = "Test query"
        prompt_kwargs = {"test": "value"}

        # Act
        result = await completion_executor.execute(
            user_query=user_query,
            system_prompt=mock_prompt,
            tool_manager=mock_tool_manager,
            prompt_kwargs=prompt_kwargs,
        )

        # Assert
        mock_client.fcall.assert_called_once_with(
            user_query=user_query,
            system_prompt=mock_prompt,
            tool_manager=mock_tool_manager,
            prompt_kwargs=prompt_kwargs,
        )
        assert result == {"success": True}

    def test_inheritance(self, completion_executor):
        """Test that CompletionExecutor inherits from BaseExecutor."""
        from tron_intelligence.executors.base import BaseExecutor

        assert isinstance(completion_executor, BaseExecutor)
