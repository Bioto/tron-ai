import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from tron_intelligence.executors.agents.builtin.search_agent import (
    SearchAgent,
    perplexity_config_exists,
)
from tron_intelligence.executors.agents.models.agent import Agent
from adalflow.core.tool_manager import ToolManager


class TestSearchAgent:
    """Tests for the SearchAgent class."""

    @pytest.fixture
    def search_agent(self):
        """Fixture for a SearchAgent instance."""
        return SearchAgent()

    def test_inheritance(self, search_agent):
        """Test that SearchAgent inherits from Agent."""
        assert isinstance(search_agent, Agent)

    def test_initialization(self, search_agent):
        """Test that SearchAgent initializes correctly."""
        assert search_agent.name == "Search Agent"
        assert "manages search operations" in search_agent.description.lower()
        assert search_agent.prompt is not None
        assert search_agent.tool_manager is not None
        assert isinstance(search_agent.tool_manager, ToolManager)
        assert search_agent.supports_multiple_operations is True

    def test_tools_available(self, search_agent):
        """Test that search tools are available in the agent."""
        tools = search_agent.tool_manager._components.get("tools", [])

        # Verify we have the expected search tools
        tool_functions = [tool.fn.__name__ for tool in tools]
        expected_functions = [
            "query_perplexity",
            "search_with_context",
            "batch_search",
        ]

        for expected_function in expected_functions:
            assert expected_function in tool_functions

    @patch("tron_intelligence.executors.agents.builtin.search_agent.config")
    def test_perplexity_config_exists_true(self, mock_config):
        """Test perplexity_config_exists when config exists."""
        # Setup
        mock_config.PERPLEXITY_API_KEY = "test-api-key"
        mock_config.PERPLEXITY_MODEL = "test-model"

        # Execute & verify
        assert perplexity_config_exists() is True

    @patch("tron_intelligence.executors.agents.builtin.search_agent.config")
    def test_perplexity_config_exists_false_no_key(self, mock_config):
        """Test perplexity_config_exists when API key is missing."""
        # Setup
        mock_config.PERPLEXITY_API_KEY = None
        mock_config.PERPLEXITY_MODEL = "test-model"

        # Execute & verify
        assert perplexity_config_exists() is False

    @patch("tron_intelligence.executors.agents.builtin.search_agent.config")
    def test_perplexity_config_exists_false_no_model(self, mock_config):
        """Test perplexity_config_exists when model is missing."""
        # Setup
        mock_config.PERPLEXITY_API_KEY = "test-api-key"
        mock_config.PERPLEXITY_MODEL = None

        # Execute & verify
        assert perplexity_config_exists() is False

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.perplexity_config_exists")
    @patch("aiohttp.ClientSession.post")
    async def test_query_perplexity_success(self, mock_post, mock_config_exists):
        """Test the query_perplexity tool for successful case."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import query_perplexity

        # Setup
        mock_config_exists.return_value = True
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "choices": [
                    {"message": {"content": "Search result"}, "finish_reason": "stop"}
                ],
                "model": "test-model",
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                "created": 12345,
                "id": "response-id",
            }
        )
        mock_post.return_value.__aenter__.return_value = mock_response

        # Execute
        result = await query_perplexity(
            query="test query", api_key="test-api-key", model="test-model"
        )

        # Verify
        assert result["success"] is True
        assert result["response"] == "Search result"
        assert result["model"] == "test-model"
        assert "usage" in result
        assert "metadata" in result
        assert result["metadata"]["finish_reason"] == "stop"

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.perplexity_config_exists")
    async def test_query_perplexity_no_config(self, mock_config_exists):
        """Test the query_perplexity tool when config is missing."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import query_perplexity

        # Setup
        mock_config_exists.return_value = False

        # Execute
        result = await query_perplexity(query="test query")

        # Verify
        assert "error" in result
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.perplexity_config_exists")
    @patch("aiohttp.ClientSession.post")
    async def test_query_perplexity_api_error(self, mock_post, mock_config_exists):
        """Test the query_perplexity tool when API returns an error."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import query_perplexity

        # Setup
        mock_config_exists.return_value = True
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="API Error")
        mock_post.return_value.__aenter__.return_value = mock_response

        # Execute
        result = await query_perplexity(query="test query")

        # Verify
        assert "error" in result
        assert "API request failed" in result["error"]
        assert result["details"] == "API Error"

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.query_perplexity")
    async def test_search_with_context(self, mock_query_perplexity):
        """Test the search_with_context tool."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import search_with_context

        # Setup
        mock_query_perplexity.return_value = {
            "success": True,
            "response": "Search result with context",
        }

        # Execute
        result = await search_with_context(
            query="test query", context="additional context information"
        )

        # Verify
        mock_query_perplexity.assert_called_once()
        assert (
            "Context: additional context information"
            in mock_query_perplexity.call_args[0][0]
        )
        assert "Query: test query" in mock_query_perplexity.call_args[0][0]
        assert result["success"] is True
        assert result["response"] == "Search result with context"

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.perplexity_config_exists")
    async def test_search_with_context_no_config(self, mock_config_exists):
        """Test the search_with_context tool when config is missing."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import search_with_context

        # Setup
        mock_config_exists.return_value = False

        # Execute
        result = await search_with_context(query="test query", context="test context")

        # Verify
        assert "error" in result
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.query_perplexity")
    @patch("tron_intelligence.executors.agents.builtin.search_agent.perplexity_config_exists")
    async def test_batch_search_success(
        self, mock_config_exists, mock_query_perplexity
    ):
        """Test the batch_search tool for successful case."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import batch_search

        # Setup
        mock_config_exists.return_value = True
        mock_query_perplexity.side_effect = [
            {"success": True, "response": "Result 1"},
            {"success": True, "response": "Result 2"},
            {"success": False, "error": "Failed"},
        ]

        # Execute
        result = await batch_search(queries=["query1", "query2", "query3"])

        # Verify
        assert mock_query_perplexity.call_count == 3
        assert result["success"] is True
        assert len(result["results"]) == 3
        assert result["summary"]["total_queries"] == 3
        assert result["summary"]["successful_queries"] == 2
        assert result["summary"]["failed_queries"] == 1

    @pytest.mark.asyncio
    @patch("tron_intelligence.executors.agents.builtin.search_agent.perplexity_config_exists")
    async def test_batch_search_no_config(self, mock_config_exists):
        """Test the batch_search tool when config is missing."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.search_agent import batch_search

        # Setup
        mock_config_exists.return_value = False

        # Execute
        result = await batch_search(queries=["query1", "query2"])

        # Verify
        assert "error" in result
        assert "not configured" in result["error"]
