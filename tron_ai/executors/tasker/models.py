from pydantic import BaseModel, Field
from tron_ai.modules.tasks import Task
from tron_ai.models.agent import Agent
from typing import List, Optional
from tron_ai.models.prompts import PromptMeta, ToolCall


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
    
    
class AgentRouterSelectedAgent(BaseModel):
    """Represents a selected agent and task pairing from the router.

    This model captures the mapping between an agent and the specific task they were selected to handle.
    It is used to track which agents were assigned to which tasks during the routing process.

    Attributes:
        agent_name (str): The name identifier of the selected agent
        task_id (str): The unique identifier of the task this agent was selected for
    """

    agent_name: str = Field(description="The name identifier of the selected agent")
    task_id: str = Field(
        description="The unique identifier of the task this agent was selected for"
    )


class AgentRouterResults(PromptMeta, BaseModel):
    """Results from the agent router containing the selected agent-task pairings and confidence score.

    This model represents the output from the agent router which determines the most appropriate
    agent to handle each task based on agent capabilities and task requirements. The router
    analyzes the available agents and tasks to create optimal one-to-one pairings that maximize
    the likelihood of successful task completion.

    Attributes:
        selected_agents (List[AgentRouterSelectedAgent]): A list of agent-task pairings, where each
            pairing is represented by a single AgentRouterSelectedAgent object containing one agent name
            and one task ID. The list will be empty if no suitable agent-task matches were found.
            Each agent can only be paired with one task, and each task can only be assigned to one agent.

        confidence (Optional[float]): A confidence score between 0 and 1 indicating the router's
            assessment of how well the selected one-to-one agent-task pairings match. Higher scores
            (closer to 1) indicate stronger matches where agents are highly qualified for their assigned
            tasks. Lower scores (closer to 0) suggest less optimal matches. Will be None if no agents
            were selected. This score considers factors like agent capabilities, task requirements,
            and the overall fit of the assignments.
    """

    selected_agents: List[AgentRouterSelectedAgent] = Field(
        description="List of agent-task pairings, each containing an agent name and their assigned task ID",
        default=[],
    )
    confidence: Optional[float] = Field(
        description="Confidence score (0-1) indicating the quality of the agent-task matches",
        default=None,
    )

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