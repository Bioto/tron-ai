# Third-party imports
from adalflow.core.tool_manager import ToolManager

# Local imports
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.prompts.models import Prompt
from adalflow.core.func_tool import FunctionTool

from tron_intelligence.utils import file_manager


# Create tool manager with code analysis tools
code_tools = ToolManager(
    tools=[
        FunctionTool(fn=file_manager.create_file),
        FunctionTool(fn=file_manager.read_file),
        FunctionTool(fn=file_manager.update_file),
        FunctionTool(fn=file_manager.delete_file),
        FunctionTool(fn=file_manager.list_directory),
    ]
)


class CodeAgent(Agent):
    """Code analysis and management agent."""

    def __init__(self):
        super().__init__(
            name="Professional Software Developer",
            description="Professional Software Developer with all programming languages and frameworks knowledge",
            prompt=Prompt.from_string(
                """
                You are a professional software developer. Your role is to directly implement solutions using the available tools:

                - create_file: Creates new files with content
                - read_file: Retrieves file contents
                - update_file: Modifies existing files
                - delete_file: Removes files
                - list_directory: Shows directory contents

                Execute tasks directly without explaining the process.
                
                Never look at node_modules directory.
                
                All of your interactions should be using tool calls unless the user asks you to do something that is not possible with the tools.
                """
            ),
            tools=code_tools,
        )
