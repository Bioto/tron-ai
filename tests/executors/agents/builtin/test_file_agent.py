import pytest
from unittest.mock import patch

from tron_ai.executors.agents.builtin.file_agent import FileAgent
from adalflow.core.tool_manager import ToolManager
from tron_ai.executors.agents.models.agent import Agent


class TestFileAgent:
    """Tests for the FileAgent class."""

    @pytest.fixture
    def file_agent(self):
        """Fixture for a FileAgent instance."""
        return FileAgent()

    def test_initialization(self, file_agent):
        """Test that FileAgent initializes correctly with expected properties."""
        # Assert
        # and description
        assert file_agent.name == "File Manager"
        assert "file system operations" in file_agent.description.lower()

        # Assert correct prompt is set
        assert file_agent.prompt is not None
        prompt_text = file_agent.prompt.text
        assert "file system operations expert" in prompt_text
        assert "file operations" in prompt_text.lower()
        assert "directory management" in prompt_text.lower()

        # Assert tools are set to a ToolManager instance and have the correct number of tools
        assert isinstance(file_agent.tool_manager, ToolManager)
        assert len(file_agent.tool_manager.tools) == 5

    def test_inheritance(self, file_agent):
        """Test that FileAgent inherits from Agent base class."""
        assert isinstance(file_agent, Agent)

    def test_tools_availability(self, file_agent):
        """Test that all required tools are available in the agent's tool set."""
        # Check if critical file operation tools are available
        tool_manager = file_agent.tool_manager
        tool_names = [tool.fn.__name__ for tool in tool_manager.tools]

        # Essential file operations that should be present
        essential_tools = [
            "create_file",
            "read_file",
            "update_file",
            "delete_file",
            "list_directory",
        ]

        # Verify all essential tools are available
        for tool_name in essential_tools:
            assert tool_name in tool_names, (
                f"Required tool {tool_name} not found in FileAgent tools"
            )

    @patch("tron_ai.utils.file_manager.create_file")
    async def test_create_file_tool_called(self, mock_create_file, file_agent):
        """Test that the create_file tool is properly callable."""
        # Setup mock
        mock_create_file.return_value = {
            "success": True,
            "message": "File created successfully",
        }

        # Get the tool function
        create_file_tool = next(
            tool for tool in file_agent.tool_manager.tools if tool.fn.__name__ == "create_file"
        )
        create_file_tool.fn = mock_create_file  # Ensure the tool uses the mock

        # Call the tool function
        result = await create_file_tool.acall("test.txt", "Test content")

        # Verify the correct function was called with correct arguments
        mock_create_file.assert_called_once_with("test.txt", "Test content")
        assert result.output["success"] is True

    @patch("tron_ai.utils.file_manager.read_file")
    async def test_read_file_tool_called(self, mock_read_file, file_agent):
        """Test that the read_file tool is properly callable."""
        # Setup mock
        mock_read_file.return_value = {
            "success": True,
            "content": "File content",
            "metadata": {"size": 12},
        }

        # Get the tool function
        read_file_tool = next(
            tool for tool in file_agent.tool_manager.tools if tool.fn.__name__ == "read_file"
        )
        read_file_tool.fn = mock_read_file  # Ensure the tool uses the mock

        # Call the tool function
        result = await read_file_tool.acall("test.txt")

        # Verify the correct function was called with correct arguments
        mock_read_file.assert_called_once_with("test.txt")
        assert result.output["success"] is True
        assert result.output["content"] == "File content"

    @patch("tron_ai.utils.file_manager.update_file")
    async def test_update_file_tool_called(self, mock_update_file, file_agent):
        """Test that the update_file tool is properly callable."""
        # Setup mock
        mock_update_file.return_value = {
            "success": True,
            "message": "File updated successfully",
        }

        # Get the tool function
        update_file_tool = next(
            tool for tool in file_agent.tool_manager.tools if tool.fn.__name__ == "update_file"
        )
        update_file_tool.fn = mock_update_file  # Ensure the tool uses the mock

        # Call the tool function
        result = await update_file_tool.acall(
            "test.txt", "Updated content", True, False
        )

        # Verify the correct function was called with correct arguments
        mock_update_file.assert_called_once_with(
            "test.txt", "Updated content", True, False
        )
        assert result.output["success"] is True

    @patch("tron_ai.utils.file_manager.delete_file")
    async def test_delete_file_tool_called(self, mock_delete_file, file_agent):
        """Test that the delete_file tool is properly callable."""
        # Setup mock
        mock_delete_file.return_value = {
            "success": True,
            "message": "File deleted successfully",
        }

        # Get the tool function
        delete_file_tool = next(
            tool for tool in file_agent.tool_manager.tools if tool.fn.__name__ == "delete_file"
        )
        delete_file_tool.fn = mock_delete_file  # Ensure the tool uses the mock

        # Call the tool function
        result = await delete_file_tool.acall("test.txt", True)

        # Verify the correct function was called with correct arguments
        mock_delete_file.assert_called_once_with("test.txt", True)
        assert result.output["success"] is True

    @patch("tron_ai.utils.file_manager.list_directory")
    async def test_list_directory_tool_called(self, mock_list_directory, file_agent):
        """Test that the list_directory tool is properly callable."""
        # Setup mock
        mock_list_directory.return_value = {
            "success": True,
            "items": [
                {"name": "file1.txt", "type": "file"},
                {"name": "file2.txt", "type": "file"},
            ],
            "metadata": {"count": 2, "files": 2, "directories": 0},
        }

        # Get the tool function
        list_directory_tool = next(
            tool
            for tool in file_agent.tool_manager.tools
            if tool.fn.__name__ == "list_directory"
        )
        list_directory_tool.fn = mock_list_directory  # Ensure the tool uses the mock

        # Call the tool function
        result = await list_directory_tool.acall("/test/dir", True, False, "*.txt")

        # Verify the correct function was called with correct arguments
        mock_list_directory.assert_called_once_with("/test/dir", True, False, "*.txt")
        assert result.output["success"] is True
        assert "items" in result.output

    def test_tool_signatures(self, file_agent):
        """Test that tool signatures match expected parameters."""
        # Check if tool parameters match expected signatures
        for tool in file_agent.tool_manager.tools:
            if tool.fn.__name__ == "create_file":
                assert "file_path" in tool.definition.func_parameters["properties"]
                assert "content" in tool.definition.func_parameters["properties"]
                assert "overwrite" in tool.definition.func_parameters["properties"]
            elif tool.fn.__name__ == "read_file":
                assert "file_path" in tool.definition.func_parameters["properties"]
            elif tool.fn.__name__ == "update_file":
                assert "file_path" in tool.definition.func_parameters["properties"]
                assert "content" in tool.definition.func_parameters["properties"]
                assert "append" in tool.definition.func_parameters["properties"]
                assert (
                    "create_if_missing" in tool.definition.func_parameters["properties"]
                )
            elif tool.fn.__name__ == "delete_file":
                assert "file_path" in tool.definition.func_parameters["properties"]
                assert "force" in tool.definition.func_parameters["properties"]
            elif tool.fn.__name__ == "list_directory":
                assert "directory_path" in tool.definition.func_parameters["properties"]
                assert "recursive" in tool.definition.func_parameters["properties"]
                assert "include_hidden" in tool.definition.func_parameters["properties"]
                assert "pattern" in tool.definition.func_parameters["properties"]
