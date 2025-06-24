"""Simple tests for the file manager module."""

import pytest
from unittest.mock import patch

from tron_intelligence.utils.file_manager import (
    create_file,
    read_file,
    update_file,
    delete_file,
    list_directory,
)


class TestFileManagerFunctions:
    """Test suite for file manager async functions."""

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.write_file_async")
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_create_file_success(self, mock_exists_async, mock_write_async):
        """Test successful file creation."""
        mock_exists_async.return_value = False
        mock_write_async.return_value = 13  # Length of "Hello, world!"

        result = await create_file("test.txt", "Hello, world!")

        assert result["success"] is True
        assert "created successfully" in result["message"]
        mock_write_async.assert_called_once_with("test.txt", "Hello, world!")

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_create_file_already_exists(self, mock_exists_async):
        """Test file creation when file already exists."""
        mock_exists_async.return_value = True

        result = await create_file("test.txt", "Hello", overwrite=False)

        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.get_file_stats_async")
    @patch("tron_intelligence.utils.file_manager.read_file_async")
    @patch("tron_intelligence.utils.file_manager.is_file_async")
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_read_file_success(
        self, mock_exists_async, mock_isfile_async, mock_read_async, mock_stats_async
    ):
        """Test successful file reading."""
        mock_exists_async.return_value = True
        mock_isfile_async.return_value = True
        mock_read_async.return_value = "File content"
        mock_stats_async.return_value = {
            "size": 100,
            "last_modified": 1234567890,
            "created": 1234560000,
            "mode": 0o100644,
        }

        result = await read_file("test.txt")

        assert result["success"] is True
        assert result["content"] == "File content"
        assert result["metadata"]["size"] == 100

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_read_file_not_found(self, mock_exists_async):
        """Test reading non-existent file."""
        mock_exists_async.return_value = False

        result = await read_file("test.txt")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.get_file_stats_async")
    @patch("tron_intelligence.utils.file_manager.write_file_async")
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_update_file_success(
        self, mock_exists_async, mock_write_async, mock_stats_async
    ):
        """Test successful file update."""
        mock_exists_async.return_value = True
        mock_write_async.return_value = 11  # Length of "New content"
        mock_stats_async.return_value = {
            "size": 100,
            "last_modified": 1234567890,
            "created": 1234560000,
            "mode": 0o100644,
        }

        result = await update_file("test.txt", "New content")

        assert result["success"] is True
        assert "updated successfully" in result["message"]
        mock_write_async.assert_called_once_with("test.txt", "New content")

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.delete_file_async")
    @patch("tron_intelligence.utils.file_manager.is_file_async")
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_delete_file_success(
        self, mock_exists_async, mock_isfile_async, mock_delete_async
    ):
        """Test successful file deletion."""
        mock_exists_async.return_value = True
        mock_isfile_async.return_value = True
        mock_delete_async.return_value = True

        result = await delete_file("test.txt")

        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_delete_async.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.file_manager.list_directory_async")
    @patch("tron_intelligence.utils.file_manager.is_directory_async")
    @patch("tron_intelligence.utils.file_manager.file_exists_async")
    async def test_list_directory_success(
        self,
        mock_exists_async,
        mock_isdir_async,
        mock_listdir_async,
    ):
        """Test successful directory listing."""
        mock_exists_async.return_value = True
        mock_isdir_async.return_value = True
        mock_listdir_async.return_value = [
            {
                "name": "file1.txt",
                "path": "test_dir/file1.txt",
                "type": "file",
                "size": 100,
                "last_modified": 1234567890,
            },
            {
                "name": "file2.py",
                "path": "test_dir/file2.py",
                "type": "file",
                "size": 100,
                "last_modified": 1234567890,
            },
            {
                "name": "subdir",
                "path": "test_dir/subdir",
                "type": "directory",
                "size": None,
                "last_modified": 1234567890,
            },
        ]

        result = await list_directory("test_dir")

        assert result["success"] is True
        assert len(result["items"]) == 3
        assert result["metadata"]["count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
