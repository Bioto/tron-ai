"""
Test suite for async file I/O performance improvements.

This test validates that file operations are truly non-blocking
and provide better performance in concurrent scenarios.
"""

import os
import asyncio
import tempfile
import time
import pytest

from tron_intelligence.utils.file_manager_async import (
    read_file_async,
    write_file_async,
    append_file_async,
    delete_file_async,
    file_exists_async,
    get_file_stats_async,
    list_directory_async,
    glob_async,
)


class TestFileManagerAsync:
    """Test async file I/O operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_write_read_file_async(self, temp_dir):
        """Test basic async write and read operations."""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "Hello, async world!"

        # Test write
        chars_written = await write_file_async(file_path, content)
        assert chars_written == len(content)
        assert await file_exists_async(file_path)

        # Test read
        read_content = await read_file_async(file_path)
        assert read_content == content

    @pytest.mark.asyncio
    async def test_append_file_async(self, temp_dir):
        """Test async file append operation."""
        file_path = os.path.join(temp_dir, "append.txt")
        initial_content = "Line 1\n"
        append_content = "Line 2\n"

        # Write initial content
        await write_file_async(file_path, initial_content)

        # Append content
        await append_file_async(file_path, append_content)

        # Verify
        final_content = await read_file_async(file_path)
        assert final_content == initial_content + append_content

    @pytest.mark.asyncio
    async def test_delete_file_async(self, temp_dir):
        """Test async file deletion."""
        file_path = os.path.join(temp_dir, "delete_me.txt")

        # Create file
        await write_file_async(file_path, "Delete me")
        assert await file_exists_async(file_path)

        # Delete file
        deleted = await delete_file_async(file_path)
        assert deleted is True
        assert not await file_exists_async(file_path)

        # Try deleting non-existent file
        deleted_again = await delete_file_async(file_path)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_file_stats_async(self, temp_dir):
        """Test async file statistics retrieval."""
        file_path = os.path.join(temp_dir, "stats.txt")
        content = "Test content for stats"

        await write_file_async(file_path, content)

        stats = await get_file_stats_async(file_path)
        assert stats["size"] == len(content)
        assert "last_modified" in stats
        assert "created" in stats
        assert "mode" in stats

    @pytest.mark.asyncio
    async def test_list_directory_async(self, temp_dir):
        """Test async directory listing."""
        # Create test structure
        await write_file_async(os.path.join(temp_dir, "file1.txt"), "content1")
        await write_file_async(os.path.join(temp_dir, "file2.txt"), "content2")
        await write_file_async(os.path.join(temp_dir, ".hidden.txt"), "hidden")

        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        await write_file_async(os.path.join(subdir, "subfile.txt"), "subcontent")

        # List without hidden files
        items = await list_directory_async(
            temp_dir, recursive=False, include_hidden=False
        )
        assert len(items) == 3  # 2 files + 1 directory

        # List with hidden files
        items_with_hidden = await list_directory_async(
            temp_dir, recursive=False, include_hidden=True
        )
        assert len(items_with_hidden) == 4  # 3 files + 1 directory

        # List recursively
        items_recursive = await list_directory_async(
            temp_dir, recursive=True, include_hidden=False
        )
        # 2 files + 1 directory + 1 subfile
        assert len(items_recursive) == 4

        # List with pattern
        txt_files = await list_directory_async(
            temp_dir, pattern="*.txt", include_hidden=False
        )
        assert len(txt_files) == 2

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, temp_dir):
        """Test that multiple file operations can run concurrently without blocking."""
        num_files = 10
        content = "x" * 1000  # 1KB content

        # Create file tasks
        async def create_and_read(i: int):
            file_path = os.path.join(temp_dir, f"concurrent_{i}.txt")
            start = time.time()

            # Write file
            await write_file_async(file_path, content)

            # Read it back
            read_content = await read_file_async(file_path)
            assert read_content == content

            # Get stats
            stats = await get_file_stats_async(file_path)
            assert stats["size"] == len(content)

            return time.time() - start

        # Run operations concurrently
        start_time = time.time()
        tasks = [create_and_read(i) for i in range(num_files)]
        durations = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify files were created
        items = await list_directory_async(temp_dir)
        assert len(items) == num_files

        # Performance check: concurrent execution should be faster than sequential
        sequential_estimate = sum(durations)
        speedup = sequential_estimate / total_time
        print("\nConcurrent file operations:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Sequential estimate: {sequential_estimate:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")

        # Should have at least 2x speedup with thread pool
        assert speedup > 1.5  # Reduced threshold for CI environments

    @pytest.mark.asyncio
    async def test_large_file_performance(self, temp_dir):
        """Test performance with larger files."""
        file_path = os.path.join(temp_dir, "large_file.txt")

        # Create 10MB content
        large_content = "x" * (10 * 1024 * 1024)

        # Time write operation
        start = time.time()
        await write_file_async(file_path, large_content)
        write_time = time.time() - start

        # Time read operation
        start = time.time()
        read_content = await read_file_async(file_path)
        read_time = time.time() - start

        assert len(read_content) == len(large_content)

        print("\nLarge file operations (10MB):")
        print(f"  Write time: {write_time:.3f}s")
        print(f"  Read time: {read_time:.3f}s")

        # Cleanup
        await delete_file_async(file_path)

    @pytest.mark.asyncio
    async def test_glob_async(self, temp_dir):
        """Test async glob functionality."""
        # Create test files
        await write_file_async(os.path.join(temp_dir, "file1.txt"), "")
        await write_file_async(os.path.join(temp_dir, "file2.log"), "")
        await write_file_async(os.path.join(temp_dir, "file3.txt"), "")

        # Test glob
        txt_files = await glob_async(os.path.join(temp_dir, "*.txt"))
        assert len(txt_files) == 2
        assert os.path.join(temp_dir, "file1.txt") in txt_files
        assert os.path.join(temp_dir, "file3.txt") in txt_files

    @pytest.mark.asyncio
    async def test_error_handling(self, temp_dir):
        """Test error handling for non-existent files."""
        non_existent_file = os.path.join(temp_dir, "non_existent.txt")

        # Test read
        with pytest.raises(FileNotFoundError):
            await read_file_async(non_existent_file)

        # Test stats
        with pytest.raises(FileNotFoundError):
            await get_file_stats_async(non_existent_file)

        # Test list non-existent directory
        with pytest.raises(FileNotFoundError):
            await list_directory_async(os.path.join(temp_dir, "non_existent_dir"))


def run_tests():
    """Helper function to run tests with pytest."""
    pytest.main(["-v", __file__])


if __name__ == "__main__":
    run_tests() 