"""Tests for the async file manager functions."""

import pytest
from unittest.mock import patch
import os
import tempfile

from tron_intelligence.utils.file_manager import (
    create_file,
    read_file,
    update_file,
    delete_file,
    list_directory,
    FileManagerTools,
)


class TestAsyncFileManager:
    """Test suite for async file manager functions."""

    @pytest.mark.asyncio
    async def test_create_file_success(self):
        """Test successful file creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            content = "Hello, world!"

            result = await create_file(file_path, content)

            assert result["success"] is True
            assert "created successfully" in result["message"]
            assert result["metadata"]["path"] == file_path
            assert result["metadata"]["size"] == len(content)
            assert result["metadata"]["is_new"] is True

            # Verify file was actually created
            assert os.path.exists(file_path)
            with open(file_path, "r") as f:
                assert f.read() == content

    @pytest.mark.asyncio
    async def test_create_file_already_exists(self):
        """Test file creation when file already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            # Create file first
            with open(file_path, "w") as f:
                f.write("Original content")

            result = await create_file(file_path, "New content")

            assert result["success"] is False
            assert "already exists" in result["error"]

            # Verify original content unchanged
            with open(file_path, "r") as f:
                assert f.read() == "Original content"

    @pytest.mark.asyncio
    async def test_create_file_with_overwrite(self):
        """Test file creation with overwrite flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            # Create file first
            with open(file_path, "w") as f:
                f.write("Original content")

            result = await create_file(file_path, "New content", overwrite=True)

            assert result["success"] is True
            assert result["metadata"]["is_new"] is False

            # Verify content was overwritten
            with open(file_path, "r") as f:
                assert f.read() == "New content"

    @pytest.mark.asyncio
    async def test_create_file_creates_directories(self):
        """Test that create_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "nested", "deep", "test.txt")

            result = await create_file(file_path, "Content")

            assert result["success"] is True
            assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_create_file_error_handling(self):
        """Test create_file error handling."""
        # Try to create file in invalid location
        result = await create_file("/invalid/path/test.txt", "Content")

        assert result["success"] is False
        assert "Failed to create file" in result["error"]

    @pytest.mark.asyncio
    async def test_read_file_success(self):
        """Test successful file reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            content = "Test content\nMultiple lines\n"

            with open(file_path, "w") as f:
                f.write(content)

            result = await read_file(file_path)

            assert result["success"] is True
            assert result["content"] == content
            assert result["metadata"]["path"] == file_path
            assert result["metadata"]["size"] == len(content)
            assert "last_modified" in result["metadata"]

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        """Test reading non-existent file."""
        result = await read_file("/nonexistent/file.txt")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_read_file_not_a_file(self):
        """Test reading a directory instead of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await read_file(tmpdir)

            assert result["success"] is False
            assert "not a file" in result["error"]

    @pytest.mark.asyncio
    async def test_read_file_unicode_content(self):
        """Test reading file with unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "unicode.txt")
            content = "Hello 世界! 🌍 Émojis work too!"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            result = await read_file(file_path)

            assert result["success"] is True
            assert result["content"] == content

    @pytest.mark.asyncio
    async def test_update_file_success(self):
        """Test successful file update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            # Create initial file
            with open(file_path, "w") as f:
                f.write("Original content")

            result = await update_file(file_path, "Updated content")

            assert result["success"] is True
            assert "updated successfully" in result["message"]
            assert result["metadata"]["operation"] == "update"

            # Verify content was updated
            with open(file_path, "r") as f:
                assert f.read() == "Updated content"

    @pytest.mark.asyncio
    async def test_update_file_append_mode(self):
        """Test file update in append mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            # Create initial file
            with open(file_path, "w") as f:
                f.write("Original content\n")

            result = await update_file(file_path, "Appended content\n", append=True)

            assert result["success"] is True
            assert "appended to successfully" in result["message"]
            assert result["metadata"]["operation"] == "append"

            # Verify content was appended
            with open(file_path, "r") as f:
                content = f.read()
                assert "Original content\n" in content
                assert "Appended content\n" in content

    @pytest.mark.asyncio
    async def test_update_file_not_found(self):
        """Test updating non-existent file without create flag."""
        result = await update_file("/nonexistent/file.txt", "Content")

        assert result["success"] is False
        assert "not found" in result["error"]
        assert "create_if_missing=True" in result["error"]

    @pytest.mark.asyncio
    async def test_update_file_create_if_missing(self):
        """Test updating non-existent file with create flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "new_file.txt")
            content = "New content"

            result = await update_file(file_path, content, create_if_missing=True)

            assert result["success"] is True
            assert os.path.exists(file_path)

            with open(file_path, "r") as f:
                assert f.read() == content

    @pytest.mark.asyncio
    async def test_delete_file_success(self):
        """Test successful file deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            # Create file
            with open(file_path, "w") as f:
                f.write("Content")

            result = await delete_file(file_path)

            assert result["success"] is True
            assert "deleted successfully" in result["message"]
            assert not os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self):
        """Test deleting non-existent file."""
        result = await delete_file("/nonexistent/file.txt")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_file_force_mode(self):
        """Test deleting non-existent file with force flag."""
        result = await delete_file("/nonexistent/file.txt", force=True)

        assert result["success"] is True
        assert "already doesn't exist" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_file_not_a_file(self):
        """Test deleting a directory instead of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.mkdir(subdir)

            result = await delete_file(subdir)

            assert result["success"] is False
            assert "not a file" in result["error"]
            assert "delete_directory" in result["error"]

    @pytest.mark.asyncio
    async def test_list_directory_success(self):
        """Test successful directory listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
                f.write("Content 1")
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("print('hello')")
            os.mkdir(os.path.join(tmpdir, "subdir"))
            with open(os.path.join(tmpdir, ".hidden"), "w") as f:
                f.write("Hidden")

            result = await list_directory(tmpdir)

            assert result["success"] is True
            assert len(result["items"]) == 3  # Not including hidden file
            assert result["metadata"]["files"] == 2
            assert result["metadata"]["directories"] == 1

            # Check file details
            file_items = [item for item in result["items"] if item["type"] == "file"]
            assert any(item["name"] == "file1.txt" for item in file_items)
            assert any(item["name"] == "file2.py" for item in file_items)

    @pytest.mark.asyncio
    async def test_list_directory_include_hidden(self):
        """Test directory listing with hidden files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create hidden file
            with open(os.path.join(tmpdir, ".hidden"), "w") as f:
                f.write("Hidden")

            result = await list_directory(tmpdir, include_hidden=True)

            assert result["success"] is True
            assert any(item["name"] == ".hidden" for item in result["items"])

    @pytest.mark.asyncio
    async def test_list_directory_recursive(self):
        """Test recursive directory listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            os.makedirs(os.path.join(tmpdir, "dir1", "dir2"))
            with open(os.path.join(tmpdir, "dir1", "file1.txt"), "w") as f:
                f.write("Content")
            with open(os.path.join(tmpdir, "dir1", "dir2", "file2.txt"), "w") as f:
                f.write("Content")

            result = await list_directory(tmpdir, recursive=True)

            assert result["success"] is True
            # Should include all files and directories
            assert result["metadata"]["count"] >= 4  # dir1, dir2, file1.txt, file2.txt

    @pytest.mark.asyncio
    async def test_list_directory_with_pattern(self):
        """Test directory listing with glob pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files
            with open(os.path.join(tmpdir, "test1.py"), "w") as f:
                f.write("code")
            with open(os.path.join(tmpdir, "test2.py"), "w") as f:
                f.write("code")
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("text")

            result = await list_directory(tmpdir, pattern="*.py")

            assert result["success"] is True
            assert len(result["items"]) == 2
            assert all(item["name"].endswith(".py") for item in result["items"])

    @pytest.mark.asyncio
    async def test_list_directory_recursive_with_pattern(self):
        """Test recursive directory listing with pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested Python files
            os.makedirs(os.path.join(tmpdir, "src", "tests"))
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("main")
            with open(os.path.join(tmpdir, "src", "module.py"), "w") as f:
                f.write("module")
            with open(os.path.join(tmpdir, "src", "tests", "test.py"), "w") as f:
                f.write("test")
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("readme")

            result = await list_directory(tmpdir, recursive=True, pattern="*.py")

            assert result["success"] is True
            assert len(result["items"]) == 3  # All .py files
            assert all(item["name"].endswith(".py") for item in result["items"])

    @pytest.mark.asyncio
    async def test_list_directory_not_found(self):
        """Test listing non-existent directory."""
        result = await list_directory("/nonexistent/directory")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_list_directory_not_a_directory(self):
        """Test listing a file instead of directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "file.txt")
            with open(file_path, "w") as f:
                f.write("content")

            result = await list_directory(file_path)

            assert result["success"] is False
            assert "not a directory" in result["error"]

    def test_file_manager_tools_initialization(self):
        """Test FileManagerTools initialization."""
        assert FileManagerTools is not None
        assert len(FileManagerTools.tools) == 5

        tool_names = [tool.fn.__name__ for tool in FileManagerTools.tools]
        expected_tools = [
            "create_file",
            "read_file",
            "update_file",
            "delete_file",
            "list_directory",
        ]

        for expected in expected_tools:
            assert expected in tool_names

    @pytest.mark.asyncio
    async def test_error_handling_with_permission_error(self):
        """Test error handling for permission errors."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = await create_file("/test.txt", "content")

            assert result["success"] is False
            assert "Failed to create file" in result["error"]
            assert "Access denied" in result["error"]
