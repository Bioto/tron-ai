from pydantic import BaseModel, Field
from tron_ai.modules.tasks import Task
from tron_ai.models.agent import Agent
from typing import List, Optional
from tron_ai.models.prompts import PromptMeta, ToolCall
import logging
import uuid

logger = logging.getLogger(__name__)


class SwarmState(BaseModel):
    """A state model for tracking the progress and results of delegated tasks.

    This class maintains the state of a delegation workflow, including the original
    user query, the tasks to be executed, available agents, completed results,
    the final report, and the root_id for workflow lineage.

    Attributes:
        session_id: The session ID for conversation tracking.
        root_id: The root workflow/call ID for tracking all related sessions.
        user_query: The original query from the user that initiated the workflow.
        tasks: A list of Task objects representing the work to be done.
        agents: A list of Agent objects available for task execution.
        results: A list of completed Task objects with their execution results.
        report: The final compiled report of the delegation workflow.
    """
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Session ID for conversation tracking")
    repo_path: Optional[str] = Field(default=None, description="Path to the repository for context enrichment")
    root_id: Optional[str] = Field(default=None, description="Root workflow/call ID for workflow lineage")
    user_query: str = Field(default="", description="The original user query that initiated the workflow")
    tasks: List[Task] = Field(default_factory=list, description="List of tasks to be executed")
    agents: List[Agent] = Field(default_factory=list, description="Available agents for task execution")
    results: List[Task] = Field(default_factory=list, description="Completed tasks with their execution results")
    report: str = Field(default="", description="The final compiled report of the delegation workflow")
    response: Optional[str] = Field(default=None, description="Direct response when no tasks are generated")
    
    def task_report(self) -> str:
        logger.info(f"Generating task report for {len(self.tasks)} tasks")
        markdown = "# Task Execution Plan\n\n"
        for i, task in enumerate(self.tasks):
            logger.debug(f"Processing task {i+1}: {task.identifier}")
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
                # First try to get generated_output if available (for MarketerResponse and similar)
                if hasattr(task.result, 'generated_output') and task.result.generated_output:
                    result_length = len(task.result.generated_output)
                    logger.info(f"Task {i+1} has generated_output with {result_length} characters")
                    logger.debug(f"Task {i+1} generated_output preview: {task.result.generated_output[:200]}...")
                    markdown += task.result.generated_output + "\n"
                elif hasattr(task.result, 'response') and task.result.response:
                    result_length = len(task.result.response)
                    logger.info(f"Task {i+1} has result with {result_length} characters")
                    logger.debug(f"Task {i+1} result preview: {task.result.response[:200]}...")
                    markdown += task.result.response + "\n"
                else:
                    logger.info(f"Task {i+1} has result of type: {type(task.result)}")
                    markdown += f"```json\n{task.result}\n```\n"
        
        total_length = len(markdown)
        logger.info(f"Generated task report with total length: {total_length} characters")
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

        confidence_score (float): A score between 0 and 1 indicating how confident the router is in the overall agent-task assignments
    """

    selected_agents: List[AgentRouterSelectedAgent] = Field(
        description="List of agent-task pairings, each containing an agent name and their assigned task ID",
        default=[],
    )
    confidence_score: float = Field(
        description="A score between 0 and 1 indicating how confident the router is in the overall agent-task assignments",
        ge=0.0,
        le=1.0
    )
    
class SwarmResults(PromptMeta, BaseModel):
    """Results from the agent manager containing either direct responses or tasks to be executed.

    This model represents the output from the agent manager which either provides direct answers
    for simple questions or breaks down complex queries into individual tasks that need to be 
    completed in sequence or parallel based on dependencies.

    Attributes:
        response (Optional[str]): Direct response for simple questions that don't require task delegation.
        tasks (List[Task]): A list of Task objects representing the individual tasks that need
            to be completed. Each task contains its own description, dependencies, and execution
            state. Tasks are ordered based on their dependencies and optimal execution order.
        tool_calls (Optional[List[ToolCall]]): A list of tool calls made during the agent's execution.
            This helps track which tools were used to generate the task list and can be useful for
            debugging or auditing purposes.
    """

    response: Optional[str] = Field(
        default="",
        description="Direct response for simple questions that don't require task delegation"
    )

    tasks: List[Task] = Field(
        description="The list of tasks that need to be completed.", 
        default=[]
    )

    tool_calls: Optional[List[ToolCall]] = Field(
        default_factory=list, 
        description="List of tools called during agent execution"
    )