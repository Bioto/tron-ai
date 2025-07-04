import pytest
from unittest.mock import patch, AsyncMock

from tron_ai.modules.mcp.manager import MCPAgentManager as Manager

@pytest.fixture(autouse=True)
def reset_singleton():
    # Reset singleton before each test
    Manager._instance = None
    yield
    Manager._instance = None

class TestMCPAgentManager:
    @pytest.mark.asyncio
    @patch("tron_ai.modules.mcp.manager.load_mcp_server_configs")
    @patch("tron_ai.modules.mcp.manager.Agent")
    async def test_initialize_and_get_agents(self, mock_mcp_agent, mock_load_configs):
        mock_load_configs.return_value = {
            "server1": {"host": "localhost"},
            "server2": {"host": "remote"},
        }
        mock_agent1 = AsyncMock()
        mock_agent2 = AsyncMock()
        mock_mcp_agent.side_effect = [mock_agent1, mock_agent2]
        manager = Manager()
        await manager.initialize("dummy.json")
        assert manager._initialized is True
        assert set(manager.agents.keys()) == {"server1", "server2"}
        assert manager.get_default_agent() in [mock_agent1, mock_agent2]
        assert manager.get_agent("server1") == mock_agent1
        assert manager.get_agent("server2") == mock_agent2
        # Should not re-initialize
        await manager.initialize("dummy.json")
        assert mock_mcp_agent.call_count == 2

    @pytest.mark.asyncio
    @patch("tron_ai.modules.mcp.manager.Agent")
    async def test_add_agent(self, mock_mcp_agent):
        manager = Manager()
        manager._initialized = True
        manager.agents = {}
        manager.default_agent_name = None
        mock_agent = AsyncMock()
        mock_mcp_agent.return_value = mock_agent
        await manager.add_agent("server3", {"host": "h3"})
        assert "server3" in manager.agents
        assert manager.get_agent("server3") == mock_agent
        assert manager.get_default_agent() == mock_agent
        # Adding again should not duplicate
        await manager.add_agent("server3", {"host": "h3"})
        assert list(manager.agents.keys()).count("server3") == 1

    @pytest.mark.asyncio
    @patch("tron_ai.modules.mcp.manager.Agent")
    async def test_remove_agent(self, mock_mcp_agent):
        manager = Manager()
        mock_agent = AsyncMock()
        manager.agents = {"server4": mock_agent}
        manager.default_agent_name = "server4"
        await manager.remove_agent("server4")
        assert "server4" not in manager.agents
        assert manager.default_agent_name is None
        mock_agent.cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("tron_ai.modules.mcp.manager.load_mcp_server_configs")
    @patch("tron_ai.modules.mcp.manager.Agent")
    async def test_reload_agents(self, mock_mcp_agent, mock_load_configs):
        # Setup initial state
        manager = Manager()
        manager._initialized = True
        manager.agents = {"old": AsyncMock()}
        manager.default_agent_name = "old"
        # Patch cleanup
        manager.cleanup = AsyncMock()
        # Patch initialize
        orig_initialize = manager.initialize
        manager.initialize = AsyncMock()
        await manager.reload_agents("dummy.json")
        manager.cleanup.assert_awaited_once()
        manager.initialize.assert_awaited_once_with("dummy.json")
        # Restore
        manager.initialize = orig_initialize

    @pytest.mark.asyncio
    async def test_cleanup(self):
        manager = Manager()
        agent1 = AsyncMock()
        agent2 = AsyncMock()
        manager.agents = {"a": agent1, "b": agent2}
        manager.default_agent_name = "a"
        manager._initialized = True
        await manager.cleanup()
        agent1.cleanup.assert_awaited_once()
        agent2.cleanup.assert_awaited_once()
        assert manager.agents == {}
        assert manager.default_agent_name is None
        assert manager._initialized is False

    def test_singleton(self):
        m1 = Manager()
        m2 = Manager()
        assert m1 is m2 