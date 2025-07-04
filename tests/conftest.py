"""Common test fixtures for the tron_ai test suite."""

import pytest
from unittest.mock import Mock, AsyncMock

from tron_ai.utils.LLMClient import LLMClient
from tron_ai.prompts.models import Prompt
from tron_ai.executors.base import ExecutorConfig


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient with common methods."""
    client = Mock(spec=LLMClient)
    client.call = Mock(return_value={"response": "test"})
    client.fcall = AsyncMock(return_value={"response": "test"})
    client.api_client = Mock()
    client.model = "test-model"
    return client


@pytest.fixture
def mock_prompt():
    """Create a mock Prompt object."""
    prompt = Mock(spec=Prompt)
    prompt.build.return_value = "Test prompt"
    prompt.output_format = Mock()
    prompt.required_kwargs = []
    return prompt


@pytest.fixture
def base_executor_config(mock_llm_client, mock_prompt):
    """Create a basic ExecutorConfig for testing."""
    return ExecutorConfig(client=mock_llm_client, prompt=mock_prompt, logging=False)
