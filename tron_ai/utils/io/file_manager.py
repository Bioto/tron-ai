# Standard library imports

# Third-party imports
from adalflow.core.func_tool import FunctionTool
from adalflow.core.tool_manager import ToolManager

import logging

# Import async file I/O utilities
from tron_ai.utils.io.file_manager_async import (
    read_file_async,
    write_file_async,
    append_file_async,
    delete_file_async,
    file_exists_async,
    is_file_async,
    is_directory_async,
    get_file_stats_async,
    list_directory_async,
)


# File operation tools
async def create_file(
    file_path: str, content: str = "", overwrite: bool = False
) -> dict:
    """
    Creates a new file with specified content.

    Args:
        file_path (str): Path where file should be created
        content (str): Content to write to the file
        overwrite (bool): Whether to overwrite if file exists

    Returns:
        dict: Operation result and metadata
    """
    try:
        # Check if file exists and handle overwrite
        if await file_exists_async(file_path) and not overwrite:
            return {
                "success": False,
                "error": f"File already exists at {file_path}. Set overwrite=True to replace.",
            }

        # Write content to file asynchronously
        chars_written = await write_file_async(file_path, content)

        return {
            "success": True,
            "message": f"File created successfully at {file_path}",
            "metadata": {
                "path": file_path,
                "size": chars_written,
                "is_new": not (await file_exists_async(file_path) and overwrite),
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to create file: {str(e)}"}


async def read_file(file_path: str) -> dict:
    """
    Reads content from a file.

    kwargs:
        file_path (str): Path of file to read

    Returns:
        dict: File content and metadata
    """
    try:
        logging.info(f"Attempting to read file at {file_path}")

        if not await file_exists_async(file_path):
            logging.error(f"File not found at {file_path} asdsadasd")
            return {"success": False, "error": f"File not found at {file_path}"}

        if not await is_file_async(file_path):
            logging.error(f"{file_path} is not a file")
            return {"success": False, "error": f"{file_path} is not a file"}

        logging.debug(f"Opening file for reading: {file_path}")
        # Read file content asynchronously
        content = await read_file_async(file_path)

        # Get file stats asynchronously
        file_stats = await get_file_stats_async(file_path)
        logging.info(f"File read successfully: {file_path} (size={file_stats['size']})")

        return {
            "success": True,
            "content": content,
            "metadata": {
                "path": file_path,
                "size": file_stats["size"],
                "last_modified": file_stats["last_modified"],
            },
        }
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {str(e)}")
        return {"success": False, "error": f"Failed to read file: {str(e)}"}


async def update_file(
    file_path: str, content: str, append: bool = False, create_if_missing: bool = False
) -> dict:
    """
    Updates content of an existing file.

    Args:
        file_path (str): Path of file to update
        content (str): New content or content to append
        append (bool): Whether to append content instead of replacing
        create_if_missing (bool): Whether to create file if it doesn't exist

    Returns:
        dict: Operation result and metadata
    """
    try:
        # Log the operation start
        logging.info(
            f"Attempting to update file at {file_path} (append={append}, create_if_missing={create_if_missing})"
        )

        # Check if file exists
        if not await file_exists_async(file_path):
            logging.warning(f"File not found at {file_path}")
            if create_if_missing:
                logging.info(f"Creating missing file at {file_path}")
                return await create_file(file_path, content)
            else:
                logging.error(
                    f"File not found and create_if_missing=False: {file_path}"
                )
                return {
                    "success": False,
                    "error": f"File not found at {file_path}. Set create_if_missing=True to create it.",
                }

        # Write or append content asynchronously
        logging.debug(f"{'Appending to' if append else 'Writing to'} file: {file_path}")
        if append:
            await append_file_async(file_path, content)
        else:
            await write_file_async(file_path, content)

        # Get updated file stats
        file_stats = await get_file_stats_async(file_path)
        logging.info(
            f"File {'appended to' if append else 'updated'} successfully: {file_path} (size={file_stats['size']})"
        )

        return {
            "success": True,
            "message": f"File {'appended to' if append else 'updated'} successfully at {file_path}",
            "metadata": {
                "path": file_path,
                "operation": "append" if append else "update",
                "size": file_stats["size"],
                "last_modified": file_stats["last_modified"],
            },
        }
    except Exception as e:
        logging.error(f"Failed to update file {file_path}: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Failed to update file: {str(e)}"}


async def delete_file(file_path: str, force: bool = False) -> dict:
    """
    Deletes a file from the filesystem.

    Args:
        file_path (str): Path of file to delete
        force (bool): Whether to ignore errors if file doesn't exist

    Returns:
        dict: Operation result and metadata

    Note:
        This tool should not be used if the file is already deleted. Use the 'force'
        parameter if you're unsure about the file's existence.
    """
    try:
        if not await file_exists_async(file_path):
            if force:
                return {
                    "success": True,
                    "message": f"File already doesn't exist at {file_path}",
                }
            else:
                return {"success": False, "error": f"File not found at {file_path}"}

        if not await is_file_async(file_path):
            return {
                "success": False,
                "error": f"{file_path} is not a file. Use delete_directory for directories.",
            }

        # Delete the file asynchronously
        await delete_file_async(file_path)

        return {
            "success": True,
            "message": f"File deleted successfully from {file_path}",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to delete file: {str(e)}"}


async def list_directory(
    directory_path: str,
    recursive: bool = False,
    include_hidden: bool = False,
    pattern: str = None,
) -> dict:
    """
    Lists files and directories in the specified directory.

    Args:
        directory_path (str): Path of directory to list
        recursive (bool): Whether to list files recursively
        include_hidden (bool): Whether to include hidden files
        pattern (str): Optional glob pattern to filter results

    Returns:
        dict: List of files and directories with metadata
    """
    try:
        if not await file_exists_async(directory_path):
            return {
                "success": False,
                "error": f"Directory not found at {directory_path}",
            }

        if not await is_directory_async(directory_path):
            return {"success": False, "error": f"{directory_path} is not a directory"}

        # List directory contents asynchronously
        items = await list_directory_async(
            directory_path, recursive, include_hidden, pattern
        )

        # Calculate metadata
        file_count = sum(1 for item in items if item["type"] == "file")
        dir_count = sum(1 for item in items if item["type"] == "directory")

        return {
            "success": True,
            "items": items,
            "metadata": {
                "directory": directory_path,
                "count": len(items),
                "files": file_count,
                "directories": dir_count,
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to list directory: {str(e)}"}


# Create tool manager with file management tools
FileManagerTools = ToolManager(
    tools=[
        FunctionTool(fn=create_file),
        FunctionTool(fn=read_file),
        FunctionTool(fn=update_file),
        FunctionTool(fn=delete_file),
        FunctionTool(fn=list_directory),
    ]
)
