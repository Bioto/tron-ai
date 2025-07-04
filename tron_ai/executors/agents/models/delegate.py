from pydantic import BaseModel, Field
from tron_ai.modules.tasks import Task
from tron_ai.executors.agents.models.agent import Agent

from typing import List


class DelegateState(BaseModel):
    """A state model for tracking the progress and results of delegated tasks.

    This class maintains the state of a delegation workflow, including the original
    user query, the tasks to be executed, available agents, completed results,
    and the final report.

    Attributes:
        user_query: The original query from the user that initiated the workflow.
        tasks: A list of Task objects representing the work to be done.
        agents: A list of Agent objects available for task execution.
        results: A list of completed Task objects with their execution results.
        report: The final compiled report of the delegation workflow.
    """
    user_query: str = Field(default="", description="The original user query that initiated the workflow")
    tasks: List[Task] = Field(default_factory=list, description="List of tasks to be executed")
    agents: List[Agent] = Field(default_factory=list, description="Available agents for task execution")
    results: List[Task] = Field(default_factory=list, description="Completed tasks with their execution results")
    report: str = Field(default="", description="The final compiled report of the delegation workflow")
    
    def task_report(self) -> str:
        markdown = "# Task Execution Plan\n\n"
        for i, task in enumerate(self.tasks):
            markdown += f"## Task {i + 1}: {task.description}\n\n"
            markdown += f"- **ID**: `{task.identifier}`\n"
            markdown += f"- **Priority**: {task.priority}\n"
            if task.dependencies:
                markdown += (
                    "- **Dependencies**: "
                    + ", ".join([f"`{dep}`" for dep in task.dependencies])
                    + "\n"
                )
            else:
                markdown += "- **Dependencies**: None\n"
            markdown += "\n### Operations:\n\n"
            for j, operation in enumerate(task.operations):
                markdown += f"{j + 1}. {operation}\n"
            markdown += "\n"
            if task.result:
                markdown += "## Results\n\n"
                if hasattr(task.result, 'response') and task.result.response:
                    markdown += task.result.response + "\n"
                else:
                    markdown += f"```json\n{task.result}\n```\n"
        return markdown