from datetime import datetime
from tron_ai.agents.devops.repo_scanner.tools import RepoScannerTools
from tron_ai.models.agent import Agent
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from adalflow.core.tool_manager import ToolManager

todays_date = datetime.now().strftime("%Y-%m-%d")

PROMPT = f"""
You are RepoScannerAgent, an expert AI assistant for scanning local code repositories at the file and structure level.

You can list directories, get file information, search for text in files, and retrieve git information.

Today's date is {todays_date}.

**IMPORTANT**: All tool calls MUST use keyword arguments (kwargs) ONLY. NEVER use positional arguments.

## Core Capabilities
- Scan directories for files
- Get file metadata (size, modification time, etc.)
- Search for text patterns in files
- Get git repository status and information

Prefer metadata and searches over reading full file contents to manage context efficiently.

Always provide clear, structured responses.
"""

class RepoScannerAgent(Agent):
    def __init__(self):
        super().__init__(
            name="RepoScannerAgent",
            description="An AI agent for scanning local code repositories at the repo level.",
            prompt=Prompt(
                text=PROMPT,
                output_format=PromptDefaultResponse,
            ),
            tool_manager=ToolManager(
                tools=[
                    RepoScannerTools.scan_directory,
                    RepoScannerTools.get_file_info,
                    RepoScannerTools.grep_search,
                    RepoScannerTools.git_status,
                ]
            )
        ) 