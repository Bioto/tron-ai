from pydantic import BaseModel, Field
from typing import List, Optional, Any
import os

from tron_intelligence.executors.agents.models.agent import Agent


class Task(BaseModel):
    """A task model representing a unit of work to be executed by an agent.

    This model represents a task that needs to be completed as part of a larger workflow.
    Each task is assigned to a single agent but can include multiple operations that the
    agent will execute in sequence.

    Attributes:
        identifier (str): A unique 16-character hex string identifier for the task. Auto-generated
            using os.urandom if not provided.
        description (str): A human-readable description of what the task will accomplish. Must be
            at least 3 characters long.
        operations (List[str]): List of operations the agent should perform in sequence.
        agent (Agent): The agent that will execute all operations in this task.
        dependencies (List[str]): List of task identifiers that must complete first.
        result (Optional[Any]): The combined output from all operations. None if not yet executed.
        error (Optional[str]): Any error message from failed execution. None if successful or not run.
        done (bool): Flag indicating if all operations in the task have completed.
        priority (int): Priority level of the task (higher number means higher priority).
    """

    model_config = {"arbitrary_types_allowed": True}

    # Metadata
    identifier: str = Field(
        default_factory=lambda: os.urandom(8).hex(),  # Shorter ID for usability
        description="Unique task identifier (16-character hex string)",
    )
    description: str = Field(
        description="Human-readable description of what the task will accomplish",
        min_length=3,
        default="",
    )
    operations: List[str] = Field(
        default_factory=list,
        description="List of operations the agent should perform in sequence",
    )

    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs that must complete first",
    )

    # Execution state
    result: Optional[Any] = None
    error: Optional[str] = None
    done: bool = False
    priority: int = Field(
        default=0,
        description="Priority level of the task (higher number means higher priority)",
    )

    def reset(self):
        """Reset task state for re-execution.

        Clears the result, error and done fields to allow the task to be executed again.
        This is useful for retrying failed tasks or re-running workflows.
        """
        self.result = None
        self.error = None
        self.done = False
        
class AgentAssignedTask(Task):
    agent: Agent = Field(default=None, description="Agent that will execute all operations in this task.")