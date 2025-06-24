# Third-party imports
from adalflow.core.func_tool import FunctionTool
from adalflow.core.tool_manager import ToolManager

# Local imports
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.prompts.models import Prompt
from tron_intelligence.utils.file_manager import (
    create_file,
    read_file,
    update_file,
    delete_file,
    list_directory,
)


class FileAgent(Agent):
    """File system operations agent."""

    def __init__(self):
        # Create tool manager with file management tools
        file_tools = ToolManager(
            tools=[
                FunctionTool(fn=create_file),
                FunctionTool(fn=read_file),
                FunctionTool(fn=update_file),
                FunctionTool(fn=delete_file),
                FunctionTool(fn=list_directory),
            ]
        )

        super().__init__(
            name="File Manager",
            description="Manages file system operations and file handling tasks",
            prompt=Prompt(
                text="""You are a file system operations expert.

Your responsibilities include:
1. File Operations
   - Create files with specified content
   - Read file contents
   - Update existing files
   - Delete files when needed

2. Directory Management
   - List directory contents
   - Navigate directory structures
   - Filter files and directories
   - Handle recursive directory operations

3. File Metadata
   - Track file sizes
   - Monitor last modified timestamps
   - Distinguish between files and directories
   - Manage file attributes

4. Error Handling
   - Provide clear error messages
   - Handle file not found scenarios
   - Manage permission issues
   - Report operation success/failure

5. Security Considerations
   - Validate file paths
   - Handle hidden files appropriately
   - Respect file system permissions
   - Prevent unauthorized access

Always follow these best practices:
- Check if files exist before operations
- Create parent directories when needed
- Provide detailed operation results
- Include relevant metadata in responses
- Handle exceptions gracefully
- Use proper encoding for file operations"""
            ),
            tool_manager=file_tools,
        )
