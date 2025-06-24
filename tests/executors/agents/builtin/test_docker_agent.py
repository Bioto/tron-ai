import pytest
from unittest.mock import patch, MagicMock

from tron_intelligence.executors.agents.builtin.docker_agent import DockerAgent
from tron_intelligence.executors.agents.models.agent import Agent
from adalflow.core.tool_manager import ToolManager


class TestDockerAgent:
    """Tests for the DockerAgent class."""

    @pytest.fixture
    def docker_agent(self):
        """Fixture for a DockerAgent instance."""
        return DockerAgent()

    def test_inheritance(self, docker_agent):
        """Test that DockerAgent inherits from Agent."""
        assert isinstance(docker_agent, Agent)

    def test_initialization(self, docker_agent):
        """Test that DockerAgent initializes correctly."""
        assert docker_agent.name == "Docker Manager"
        assert "docker containers" in docker_agent.description.lower()
        assert docker_agent.prompt is not None
        assert docker_agent.tool_manager is not None
        assert isinstance(docker_agent.tool_manager, ToolManager)

    def test_tools_available(self, docker_agent):
        """Test that Docker tools are available in the agent."""
        tools = docker_agent.tool_manager._components.get("tools", [])

        # Verify that we have the expected Docker management tools
        tool_functions = [tool.fn.__name__ for tool in tools]
        expected_functions = [
            "list_containers",
            "create_container",
            "start_container",
            "stop_container",
            "remove_container",
            "get_container_logs",
            "inspect_container",
            "run_docker_command",
        ]

        for expected_function in expected_functions:
            assert expected_function in tool_functions

    @patch("subprocess.run")
    def test_list_containers_tool(self, mock_run):
        """Test the list_containers tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = (
            '[{"ID": "123", "Names": "test-container", "Status": "Running"}]'
        )
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import list_containers

        # Execute
        result = list_containers()

        # Verify
        mock_run.assert_called_once()
        assert result.get("containers") is not None
        assert isinstance(result.get("containers"), list)

    @patch("subprocess.run")
    def test_create_container_tool(self, mock_run):
        """Test the create_container tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "container-id-123"
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import create_container

        # Execute
        result = create_container(
            image="test-image",
            name="test-container",
            ports=["8080:80"],
            env=["TEST=value"],
            volumes=["/host:/container"],
        )

        # Verify
        mock_run.assert_called_once()
        assert "container_id" in result
        assert result["container_id"] == "container-id-123"

    @patch("subprocess.run")
    def test_start_container_tool(self, mock_run):
        """Test the start_container tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import start_container

        # Execute
        result = start_container("test-container")

        # Verify
        mock_run.assert_called_once_with(
            ["docker", "start", "test-container"], capture_output=True, text=True
        )
        assert result["success"] is True
        assert "test-container" in result["message"]

    @patch("subprocess.run")
    def test_stop_container_tool(self, mock_run):
        """Test the stop_container tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import stop_container

        # Execute
        result = stop_container("test-container")

        # Verify
        mock_run.assert_called_once_with(
            ["docker", "stop", "test-container"], capture_output=True, text=True
        )
        assert result["success"] is True
        assert "test-container" in result["message"]

    @patch("subprocess.run")
    def test_remove_container_tool(self, mock_run):
        """Test the remove_container tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import remove_container

        # Execute
        result = remove_container("test-container", force=True)

        # Verify
        mock_run.assert_called_once_with(
            ["docker", "rm", "-f", "test-container"], capture_output=True, text=True
        )
        assert result["success"] is True
        assert "test-container" in result["message"]

    @patch("subprocess.run")
    def test_get_container_logs_tool(self, mock_run):
        """Test the get_container_logs tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Log line 1\nLog line 2"
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import get_container_logs

        # Execute
        result = get_container_logs("test-container", tail=10)

        # Verify
        mock_run.assert_called_once_with(
            ["docker", "logs", "--tail", "10", "test-container"],
            capture_output=True,
            text=True,
        )
        assert "logs" in result
        assert result["logs"] == "Log line 1\nLog line 2"

    @patch("subprocess.run")
    def test_inspect_container_tool(self, mock_run):
        """Test the inspect_container tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = '[{"Id": "123", "Name": "test-container"}]'
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import inspect_container

        # Execute
        result = inspect_container("test-container")

        # Verify
        mock_run.assert_called_once_with(
            ["docker", "inspect", "test-container"], capture_output=True, text=True
        )
        assert "info" in result
        assert isinstance(result["info"], list)

    @patch("subprocess.run")
    def test_run_docker_command_tool(self, mock_run):
        """Test the run_docker_command tool."""
        # Setup
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Command output"
        mock_run.return_value = mock_process

        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import run_docker_command

        # Execute
        result = run_docker_command("docker ps")

        # Verify
        mock_run.assert_called_once_with(
            ["docker", "ps"], capture_output=True, text=True
        )
        assert result["success"] is True
        assert result["stdout"] == "Command output"

    @patch("subprocess.run")
    def test_run_docker_command_validation(self, mock_run):
        """Test validation in run_docker_command tool."""
        # Import the function directly to test it
        from tron_intelligence.executors.agents.builtin.docker_agent import run_docker_command

        # Execute with invalid command
        result = run_docker_command("invalid command")

        # Verify
        mock_run.assert_not_called()
        assert "error" in result
        assert 'must start with "docker"' in result["error"]
