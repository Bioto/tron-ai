from datetime import datetime
from tron_ai.agents.devops.code_scanner.tools import CodeScannerTools
from tron_ai.models.agent import Agent
from tron_ai.models.prompts import Prompt, PromptDefaultResponse
from adalflow.core.tool_manager import ToolManager

todays_date = datetime.now().strftime("%Y-%m-%d")

PROMPT = f"""
You are CodeScannerAgent, an expert AI assistant for scanning and analyzing local code repositories using tree-sitter for structured parsing.
You can read files, scan directories, parse code structure (functions, classes, imports), and build structured maps to avoid large raw contexts.

Today's date is {todays_date}.

**IMPORTANT**: All tool calls MUST use keyword arguments (kwargs) ONLY. NEVER use positional arguments.

## Core Capabilities
- Scan directories for code files
- Read file contents (use sparingly for large files)
- Parse code structure with tree-sitter
- Build structured repository maps (prefer this to reduce context size)
- Analyze code structure without loading full contents
- Build dependency graphs with NetworkX
- Store graphs in Neo4j

For large repos, always prefer parsing and structured maps over raw file reading to manage context efficiently.

Always provide clear, structured responses with parsed elements when relevant.
"""

class CodeScannerAgent(Agent):
    def __init__(self):
        super().__init__(
            name="CodeScannerAgent",
            description="An AI agent for scanning and reading local code repositories.",
            prompt=Prompt(
                text=PROMPT,
                output_format=PromptDefaultResponse,
            ),
            tool_manager=ToolManager(
                tools=[
                    CodeScannerTools.scan_directory,
                    CodeScannerTools.read_file,
                    CodeScannerTools.parse_file,  # New
                    CodeScannerTools.build_structure_map,  # New
                    CodeScannerTools.build_dependency_graph,  # New
                    CodeScannerTools.query_relevant_context,  # New
                    CodeScannerTools.store_graph_to_neo4j,  # New
                ]
            )
        ) 