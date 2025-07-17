from datetime import datetime
from tron_ai.agents.devops.editor.tools import CodeEditorTools
from tron_ai.models.agent import Agent
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from adalflow.core.tool_manager import ToolManager

todays_date = datetime.now().strftime("%Y-%m-%d")

PROMPT = f"""
You are CodeEditorAgent, an expert AI agent for editing code while understanding dependencies and implications.
You can propose and apply edits based on context from repo maps.

Today's date is {todays_date}.

**IMPORTANT**: All tool calls MUST use keyword arguments (kwargs) ONLY. NEVER use positional arguments.

## Core Capabilities
- Propose code edits
- Apply code changes
- Analyze impact of changes

Always consider the full repo context when editing.
"""

class CodeEditorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="CodeEditorAgent",
            description="An AI agent for editing code with awareness of dependencies.",
            prompt=Prompt(
                text=PROMPT,
                output_format=PromptDefaultResponse,
            ),
            tool_manager=ToolManager(
                tools=[
                    CodeEditorTools.propose_edit,
                    CodeEditorTools.apply_edit,
                    CodeEditorTools.create_file,
                ]
            )
        ) 