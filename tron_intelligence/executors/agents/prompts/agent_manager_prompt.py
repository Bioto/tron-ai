from typing import List, Optional
from pydantic import BaseModel, Field
from tron_intelligence.prompts.models import Prompt, PromptMeta
from tron_intelligence.modules.tasks import Task
from tron_intelligence.prompts.models import ToolCall


BASE_MANAGER_PROMPT = """
You will analyze user queries and break them down into tasks. 

**IMPORTANT: Only treat a query as trivial if it can be answered with a simple factual response that requires NO actions, operations, or system changes. Examples of trivial queries:**
- "What is the meaning of X?"
- "Can you explain Y?"
- "What is the difference between A and B?"

**You MUST create tasks for any query that requires:**
- File operations (reading, writing, creating files)
- Code changes or analysis
- System operations
- Multiple steps or operations
- Use of any tools or external resources
- Any action that changes the system state

Task Organization Rules:
1. Group Operations by Agent Capability:
   - Combine operations that can be done by the same agent
   - Group operations that work with the same resources
   - Keep related operations together

2. Task Structure:
   - Each task is handled by ONE agent
   - A task can include multiple operations that the agent can perform
   - Operations within a task should be related and sequential

3. Operation Grouping:
   - Group operations that share the same context
   - Group operations that work with the same resources
   - Group operations that are part of the same logical flow

Example Task Organization:

BAD (Over-separated):
```
Task 1: List directory (File Agent)
Task 2: Create directory (File Agent)
Task 3: Write file (File Agent)
```

GOOD (Properly Grouped):
```
Task: "Setup Project Directory"
Operations:
  1. List current directory contents
  2. Create new project directory
  3. Write initial configuration file
Resources: Working directory, project files
Dependencies: None
```

These are the fields each task will have:
identifier (str): A unique 16-character hex string identifier for the task.
description (str): A human-readable description of what the task will accomplish.
operations (List[str]): List of operations the agent should perform in sequence.
dependencies (List[str]): List of task identifiers that must complete first.
priority (int): Priority level of the task (higher number means higher priority).
tasks (List[Task]): List of tasks that need to be completed.

Note: The agent assignment will be handled automatically by the system based on the operations.
Do not specify the agent in your response, just list the operations needed.

The task execution system will:
- Assign the appropriate agent based on operations
- Execute operations in sequence within each task
- Track task completion status
- Manage dependencies between tasks
- Handle errors and retries
- Stop execution and return empty results if any task returns empty data

Your response must include:
1. If the query is trivial and can be answered directly, provide the answer in the response field and leave the tasks list empty.
2. Otherwise, provide logically grouped tasks
3. Clear operation sequences within each task
4. Dependencies if needed
5. Expected outputs from each task

IMPORTANT: If any task execution returns empty results (e.g., no containers found, no files found, empty search results), you should:
- Return an empty tasks list in your final response
- Include a clear message in the response field explaining what was found to be empty
- Do not continue creating additional tasks if a prerequisite task returns empty results

Note: The agent assignment will be handled automatically by the system based on the operations.
Do not specify the agent in your response, just list the operations needed.

These are the agents available and their capabilities:
{% for agent in agents %}
- Name: {{agent[0]}}
  Description: {{agent[1]}}
  Supports Multiple Operations: {{'Yes' if agent[2] else 'No'}}
{% endfor %}
"""


class AgentManagerResults(PromptMeta, BaseModel):
    """Results from the agent manager containing the list of tasks to be executed.

    This model represents the output from the agent manager which breaks down user queries
    into individual tasks that need to be completed in sequence or parallel based on dependencies.

    Attributes:
        tasks (List[Task]): A list of Task objects representing the individual tasks that need
            to be completed. Each task contains its own description, dependencies, and execution
            state. Tasks are ordered based on their dependencies and optimal execution order.
        tool_calls (Optional[List[ToolCall]]): A list of tool calls made during the agent's execution.
            This helps track which tools were used to generate the task list and can be useful for
            debugging or auditing purposes.
    """

    tasks: List[Task] = Field(
        description="The list of tasks that need to be completed.", 
        default=[], 
        required=True
    )

    tool_calls: Optional[List[ToolCall]] = Field(
        default_factory=list, 
        description="List of tools called during agent execution"
    )

def build_agent_manager_prompt(prompt: str = BASE_MANAGER_PROMPT) -> Prompt:
    # Rebuild the model to ensure all forward references are resolved
    # This is needed because Task has a forward reference to Agent
    AgentManagerResults.model_rebuild()
    
    return Prompt(
        text=prompt,
        output_format=AgentManagerResults,
    )
