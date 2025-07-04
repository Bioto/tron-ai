import pytest
from unittest.mock import Mock
from pydantic import BaseModel

from tron_ai.executors.base import BaseExecutor, ExecutorConfig
from tron_ai.utils.LLMClient import LLMClient
from tron_ai.prompts.models import Prompt


class MockResponse(BaseModel):
    """Mock response model for testing."""

    value: str = "test"


class MockExecutor(BaseExecutor):
    """Concrete implementation of BaseExecutor for testing."""

    def execute(self, *args, **kwargs) -> BaseModel:
        """Mock implementation of execute method."""
        return MockResponse(value="executed")


class TestExecutorConfig:
    """Tests for the ExecutorConfig class."""

    def test_config_defaults(self):
        """Test that ExecutorConfig has expected defaults."""
        config = ExecutorConfig(client=Mock(spec=LLMClient))

        assert config.client is not None
        assert config.prompt is None
        assert config.logging is False

    def test_config_with_prompt(self):
        """Test that ExecutorConfig accepts a prompt."""
        mock_prompt = Mock(spec=Prompt)
        config = ExecutorConfig(client=Mock(spec=LLMClient), prompt=mock_prompt)

        assert config.prompt is mock_prompt


class TestBaseExecutor:
    """Tests for the BaseExecutor class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        return Mock(spec=LLMClient)

    @pytest.fixture
    def mock_prompt(self):
        """Fixture for a mock Prompt."""
        return Mock(spec=Prompt)

    @pytest.fixture
    def executor_config(self, mock_client, mock_prompt):
        """Fixture for a valid ExecutorConfig."""
        return ExecutorConfig(client=mock_client, prompt=mock_prompt)

    @pytest.fixture
    def executor(self, executor_config):
        """Fixture for a concrete MockExecutor instance."""
        return MockExecutor(config=executor_config)

    def test_initialization(self, executor, executor_config):
        """Test that BaseExecutor initializes with the given config."""
        assert executor._config is executor_config

    def test_client_property(self, executor, mock_client):
        """Test that client property returns the config's client."""
        assert executor.client is mock_client

    def test_prompt_property(self, executor, mock_prompt):
        """Test that prompt property returns the config's prompt."""
        assert executor.prompt is mock_prompt

    def test_execute_implementation(self, executor):
        """Test that the concrete implementation's execute method works."""
        result = executor.execute()
        assert isinstance(result, MockResponse)
        assert result.value == "executed"

    def test_abstract_method(self):
        """Test that BaseExecutor cannot be instantiated without implementing execute."""
        with pytest.raises(
            TypeError,
            match=r"Can't instantiate abstract class BaseExecutor without an implementation for abstract method 'execute'",
        ):
            BaseExecutor(config=ExecutorConfig(client=Mock(spec=LLMClient)))
