"""Tests for the file manager module."""

import pytest
from unittest.mock import patch

from tron_ai.utils.file_manager import (
    create_file,
    read_file,
    update_file,
    delete_file,
    list_directory,
)


class TestFileManager:
    """Test suite for file manager functions."""

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.write_file_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_create_file_success(self, mock_exists_async, mock_write_async):
        """Test successful file creation."""
        mock_exists_async.return_value = False
        mock_write_async.return_value = 12  # Length of "Hello, world!"

        result = await create_file("test.txt", "Hello, world!")

        assert result["success"] is True
        assert "created successfully" in result["message"]
        mock_write_async.assert_called_once_with("test.txt", "Hello, world!")

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_create_file_already_exists(self, mock_exists_async):
        """Test file creation when file already exists."""
        mock_exists_async.return_value = True

        result = await create_file("test.txt", "Hello, world!")

        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_create_file_with_exception(self):
        """Test file creation with exception."""
        with patch("tron_ai.utils.file_manager.file_exists_async", return_value=False):
            with patch(
                "tron_ai.utils.file_manager.write_file_async",
                side_effect=IOError("Permission denied"),
            ):
                result = await create_file("test.txt", "Hello")
                assert result["success"] is False
                assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.get_file_stats_async")
    @patch("tron_ai.utils.file_manager.read_file_async")
    @patch("tron_ai.utils.file_manager.is_file_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_read_file_success(
        self, mock_exists_async, mock_isfile_async, mock_read, mock_stats
    ):
        """Test successful file reading."""
        mock_exists_async.return_value = True
        mock_isfile_async.return_value = True
        mock_stats.return_value = {
            "size": 100,
            "last_modified": 1234567890,
            "created": 1234560000,
            "mode": 0o100644,
        }
        mock_read.return_value = "File content"

        result = await read_file("test.txt")

        assert result["success"] is True
        assert result["content"] == "File content"
        mock_read.assert_called_once_with("test.txt")

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_read_file_not_found(self, mock_exists_async):
        """Test reading non-existent file."""
        mock_exists_async.return_value = False

        result = await read_file("test.txt")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.is_file_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_read_file_not_a_file(self, mock_exists_async, mock_isfile_async):
        """Test reading something that's not a file."""
        mock_exists_async.return_value = True
        mock_isfile_async.return_value = False

        result = await read_file("test.txt")

        assert result["success"] is False
        assert "is not a file" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.get_file_stats_async")
    @patch("tron_ai.utils.file_manager.write_file_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_update_file_success(
        self, mock_exists_async, mock_write_async, mock_stats
    ):
        """Test successful file update."""
        mock_exists_async.return_value = True
        mock_write_async.return_value = 11  # Length of "New content"
        mock_stats.return_value = {
            "size": 100,
            "last_modified": 1234567890,
            "created": 1234560000,
            "mode": 0o100644,
        }

        result = await update_file("test.txt", "New content")

        mock_write_async.assert_called_once_with("test.txt", "New content")
        assert result["success"] is True
        assert "updated successfully" in result["message"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_update_file_not_found(self, mock_exists_async):
        """Test updating non-existent file."""
        mock_exists_async.return_value = False

        result = await update_file("test.txt", "New content")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.delete_file_async")
    @patch("tron_ai.utils.file_manager.is_file_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_delete_file_success(
        self, mock_exists_async, mock_isfile_async, mock_delete_async
    ):
        """Test successful file deletion."""
        mock_exists_async.return_value = True
        mock_isfile_async.return_value = True
        mock_delete_async.return_value = True

        result = await delete_file("test.txt")

        mock_delete_async.assert_called_once_with("test.txt")
        assert result["success"] is True
        assert "deleted successfully" in result["message"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_delete_file_not_found(self, mock_exists_async):
        """Test deleting non-existent file."""
        mock_exists_async.return_value = False

        result = await delete_file("test.txt")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.list_directory_async")
    @patch("tron_ai.utils.file_manager.is_directory_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_list_directory_success(
        self, mock_exists_async, mock_isdir_async, mock_listdir_async
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
        files = [item for item in result["items"] if item["type"] == "file"]
        dirs = [item for item in result["items"] if item["type"] == "directory"]
        assert len(files) == 2
        assert len(dirs) == 1

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_list_directory_not_found(self, mock_exists_async):
        """Test listing non-existent directory."""
        mock_exists_async.return_value = False

        result = await list_directory("test_dir")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @patch("tron_ai.utils.file_manager.is_directory_async")
    @patch("tron_ai.utils.file_manager.file_exists_async")
    async def test_list_directory_not_a_directory(
        self, mock_exists_async, mock_isdir_async
    ):
        """Test listing a file instead of directory."""
        mock_exists_async.return_value = True
        mock_isdir_async.return_value = False

        result = await list_directory("test.txt")

        assert result["success"] is False
        assert "not a directory" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
