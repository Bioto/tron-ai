"""
Async file I/O utilities for non-blocking file operations.

This module provides async wrappers for file operations to prevent
blocking the event loop during file I/O.
"""

import os
import asyncio
import glob as sync_glob
from typing import Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import logging

# Register cleanup
import atexit

# Create a thread pool for file operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="fileio")

logger = logging.getLogger(__name__)


async def read_file_async(file_path: str, encoding: str = "utf-8") -> str:
    """
    Read file content asynchronously without blocking the event loop.

    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    loop = asyncio.get_event_loop()

    def _read():
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()

    return await loop.run_in_executor(_executor, _read)


async def write_file_async(
    file_path: str, content: str, encoding: str = "utf-8", mode: str = "w"
) -> int:
    """
    Write content to file asynchronously without blocking the event loop.

    Args:
        file_path: Path to the file to write
        content: Content to write
        encoding: File encoding (default: utf-8)
        mode: File open mode (default: w)

    Returns:
        Number of characters written

    Raises:
        IOError: If file can't be written
    """
    loop = asyncio.get_event_loop()

    def _write():
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        with open(file_path, mode, encoding=encoding) as f:
            return f.write(content)

    return await loop.run_in_executor(_executor, _write)


async def append_file_async(
    file_path: str, content: str, encoding: str = "utf-8"
) -> int:
    """
    Append content to file asynchronously.

    Args:
        file_path: Path to the file
        content: Content to append
        encoding: File encoding (default: utf-8)

    Returns:
        Number of characters written
    """
    return await write_file_async(file_path, content, encoding, mode="a")


async def delete_file_async(file_path: str) -> bool:
    """
    Delete a file asynchronously.

    Args:
        file_path: Path to the file to delete

    Returns:
        True if file was deleted, False if it didn't exist

    Raises:
        OSError: If file can't be deleted
    """
    loop = asyncio.get_event_loop()

    def _delete():
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    return await loop.run_in_executor(_executor, _delete)


async def file_exists_async(file_path: str) -> bool:
    """
    Check if file exists asynchronously.

    Args:
        file_path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, os.path.exists, file_path)


async def is_file_async(path: str) -> bool:
    """
    Check if path is a file asynchronously.

    Args:
        path: Path to check

    Returns:
        True if path is a file, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, os.path.isfile, path)


async def is_directory_async(path: str) -> bool:
    """
    Check if path is a directory asynchronously.

    Args:
        path: Path to check

    Returns:
        True if path is a directory, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, os.path.isdir, path)


async def get_file_stats_async(file_path: str) -> Dict[str, Union[int, float]]:
    """
    Get file statistics asynchronously.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file stats (size, last_modified, etc.)

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    loop = asyncio.get_event_loop()

    def _get_stats():
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
            "created": stat.st_ctime,
            "mode": stat.st_mode,
        }

    return await loop.run_in_executor(_executor, _get_stats)


async def list_directory_async(
    directory_path: str,
    recursive: bool = False,
    include_hidden: bool = False,
    pattern: Optional[str] = None,
) -> List[Dict[str, Union[str, int, float, None]]]:
    """
    List directory contents asynchronously.

    Args:
        directory_path: Path to directory
        recursive: Whether to list recursively
        include_hidden: Whether to include hidden files
        pattern: Optional glob pattern to filter results

    Returns:
        List of file/directory information dictionaries

    Raises:
        NotADirectoryError: If path is not a directory
    """
    loop = asyncio.get_event_loop()

    def _list_directory():
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Not a directory: {directory_path}")

        result = []

        if pattern:
            # Handle pattern matching
            search_path = os.path.join(directory_path, pattern)
            if recursive:
                search_path = os.path.join(directory_path, "**", pattern)
                files = sync_glob.glob(search_path, recursive=True)
            else:
                files = sync_glob.glob(search_path)

            for file_path in files:
                # Skip hidden files if not included
                if not include_hidden and os.path.basename(file_path).startswith("."):
                    continue

                is_dir = os.path.isdir(file_path)
                result.append(
                    {
                        "name": os.path.basename(file_path),
                        "path": file_path,
                        "type": "directory" if is_dir else "file",
                        "size": None if is_dir else os.path.getsize(file_path),
                        "last_modified": os.path.getmtime(file_path),
                    }
                )
        else:
            # List without pattern
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    # Handle hidden directories
                    if not include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]

                    # Add directories
                    for dir_name in dirs:
                        if not include_hidden and dir_name.startswith("."):
                            continue

                        dir_path = os.path.join(root, dir_name)
                        result.append(
                            {
                                "name": dir_name,
                                "path": dir_path,
                                "type": "directory",
                                "size": None,
                                "last_modified": os.path.getmtime(dir_path),
                            }
                        )

                    # Add files
                    for file_name in files:
                        if not include_hidden and file_name.startswith("."):
                            continue

                        file_path = os.path.join(root, file_name)
                        result.append(
                            {
                                "name": file_name,
                                "path": file_path,
                                "type": "file",
                                "size": os.path.getsize(file_path),
                                "last_modified": os.path.getmtime(file_path),
                            }
                        )
            else:
                # List immediate contents only
                for item in os.listdir(directory_path):
                    if not include_hidden and item.startswith("."):
                        continue

                    item_path = os.path.join(directory_path, item)
                    is_dir = os.path.isdir(item_path)
                    result.append(
                        {
                            "name": item,
                            "path": item_path,
                            "type": "directory" if is_dir else "file",
                            "size": None if is_dir else os.path.getsize(item_path),
                            "last_modified": os.path.getmtime(item_path),
                        }
                    )

        return result

    return await loop.run_in_executor(_executor, _list_directory)


async def glob_async(pattern: str, recursive: bool = False) -> List[str]:
    """
    Find files matching a glob pattern asynchronously.

    Args:
        pattern: Glob pattern
        recursive: Whether to search recursively

    Returns:
        List of matching file paths
    """
    loop = asyncio.get_event_loop()

    def _glob():
        return sync_glob.glob(pattern, recursive=recursive)

    return await loop.run_in_executor(_executor, _glob)


# Cleanup function to properly shutdown the executor
def cleanup():
    """Cleanup function to shutdown the thread pool executor."""
    _executor.shutdown(wait=True)
    logger.info("Async file I/O thread pool shut down")


atexit.register(cleanup)
