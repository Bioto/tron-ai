from typing import TypeVar
import logging
from tron_ai.exceptions import ExecutionError
from tron_ai.modules.tasks import Task
from tron_ai.executors.agents.prompts import build_agent_manager_prompt
from tron_ai.executors.agents.utils.agent_selector import AgentSelector
from tron_ai.executors.agents.utils.report_generator import ReportGenerator
from tron_ai.executors.agents.utils.task_manager import TaskExecutor
from dataclasses import dataclass
from tron_ai.utils.LLMClient import LLMClient
from tron_ai.executors.agents.models.delegate import DelegateState

R = TypeVar("R")

@dataclass
class ExecutionResult:
    """Represents the final result of a series of task executions.

    This class encapsulates the outcome, including success status, a human-readable
    report, the number of tasks completed, and lists of tasks and errors.

    Attributes:
        success: A boolean indicating if the overall execution was successful.
        report: A summary report of the execution.
        tasks_completed: The number of tasks that were successfully completed.
        tasks: A list of Task objects that were part of the execution.
        errors: A list of error messages encountered during execution.
    """

    success: bool
    report: str
    tasks_completed: int
    tasks: list[Task] = None
    errors: list[str] = None

    def results(self) -> str:
        """Generates a markdown-formatted string detailing the execution plan and results.

        Returns:
            A string containing a detailed breakdown of each task, its properties,
            operations, and the result if available, formatted in markdown.
        """
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
                markdown += task.result.response + "\n"
        return markdown

class DelegateTools:
    """Orchestrates task generation, assignment, and execution using a delegate agent model.

    This class acts as the central coordinator for a multi-agent system. It takes a
    high-level user query, breaks it down into a series of executable tasks, assigns
    those tasks to the most appropriate specialized agents, executes them, and
    compiles the results into a final report.

    The process flows through several distinct states managed by a state machine:
    1.  `generate_tasks`: Creates a task list from the user's query.
    2.  `assign_agents`: Selects the best agent for each task.
    3.  `execute_tasks`: Runs the tasks using their assigned agents.
    4.  `handle_results`: Processes the outcomes and generates a report.
    """

    def __init__(self, client: LLMClient, *args, **kwargs) -> None:
        """Initializes the DelegateTools orchestrator.

        Args:
            client: An instance of LLMClient to interact with the language model.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self.logger = logging.getLogger(__name__)
        self.client = client
        self.agent_selector = AgentSelector(self.client)
        self.task_executor = TaskExecutor(self.client)
        self.report_generator = ReportGenerator(self.client)
        
    async def generate_tasks(self, state: DelegateState) -> DelegateState:
        """Generates a list of tasks by interpreting the user's query.

        This method uses the LLM to analyze the user's request and break it down
        into a structured list of `Task` objects. It builds a prompt that includes
        the available agents and asks the model to create a plan.

        Args:
            state: The current state of the delegate agent, containing the user query
                and available agents.

        Returns:
            The updated state with the `tasks` attribute populated with the
            generated tasks.

        Raises:
            ExecutionError: If the LLM call fails or returns an unexpected response.
        """
        self.logger.debug(f"Entering generate_tasks for user query: {state.user_query}")
        self.logger.info(f"Processing user query: {state.user_query}")
        try:
            task_manager_prompt = build_agent_manager_prompt()
            self.logger.debug("Built task manager prompt.")

            agents_info = [
                (agent.name, agent.description, agent.supports_multiple_operations)
                for agent in state.agents
            ]
            self.logger.debug(f"Calling LLM with agents: {agents_info}")

            response = self.client.call(
                user_query=str({"user_query": state.user_query}),
                system_prompt=task_manager_prompt,
                prompt_kwargs={"agents": agents_info},
            )
            self.logger.debug(f"LLM response received: {response}")
            if response.tasks:
                self.logger.info(f"Generated {len(response.tasks)} tasks")
                for i, task in enumerate(response.tasks):
                    self.logger.debug(f"Task {i+1}: {task.description}")
                # Update state with generated tasks
                state.tasks = response.tasks
            else:
                self.logger.debug("LLM did not generate any tasks.")

            self.logger.debug("Exiting generate_tasks.")
            return state
        except Exception as e:
            self.logger.exception(f"Error generating tasks: {str(e)}")
            raise ExecutionError(f"Failed to generate tasks: {str(e)}") from e

    async def process_tasks(self, state: DelegateState) -> DelegateState:
        """Processes the initial user query to generate and prepare tasks for execution.

        This method orchestrates the first step of the delegation process. It calls
        `generate_tasks` to create the initial task list. If no tasks are generated,
        it initializes empty lists to prevent downstream errors.

        Args:
            state: The initial state containing the user query.

        Returns:
            The updated state, now containing a list of tasks to be assigned.
        """
        self.logger.debug("Entering process_tasks.")
        state = await self.generate_tasks(state)
        if not state.tasks:
            self.logger.info("No tasks generated, using direct response")
            self.logger.debug("Initializing empty tasks and results list.")
            state.tasks = []
            state.results = []
        self.logger.debug("Exiting process_tasks.")
        return state

    async def assign_agents(self, state: DelegateState) -> DelegateState:
        """Assigns the most suitable agent to each task in the list.

        This method uses the `AgentSelector` utility to determine the best agent for
        each task based on the task's description and the agents' capabilities. It
        updates the state with the assigned tasks.

        Args:
            state: The current state containing the list of unassigned tasks.

        Returns:
            The updated state with agents assigned to each task.

        Raises:
            ExecutionError: If any tasks cannot be assigned to an agent.
        """
        self.logger.debug("Entering assign_agents.")
        self.logger.debug(f"Assigning agents for {len(state.tasks)} tasks.")
        selected_tasks, unassigned_tasks = self.agent_selector.select_agents(
            state.user_query, state.tasks, state.agents
        )
        self.logger.debug(
            f"Agent selection complete. {len(selected_tasks)} tasks assigned, {len(unassigned_tasks)} unassigned."
        )
        if not selected_tasks and not unassigned_tasks:
            self.logger.error("Error during execution: No tasks were assigned to agents")
            raise ExecutionError("No tasks were assigned to agents")
        if unassigned_tasks:
            self.logger.error(
                f"Error during execution: Could not assign agents to tasks: {', '.join(t.description for t in unassigned_tasks)}"
            )
            raise ExecutionError(
                f"Could not assign agents to tasks: {', '.join(t.description for t in unassigned_tasks)}"
            )
        state.tasks = selected_tasks
        self.logger.debug("Exiting assign_agents.")
        return state

    async def execute_tasks(self, state: DelegateState) -> DelegateState:
        """Executes all assigned tasks and updates the state with the results.

        This method uses the `TaskExecutor` to run the operations for each task.
        The execution can happen sequentially or in parallel, depending on the
        `TaskExecutor`'s implementation. Results from each task are stored.

        Args:
            state: The current state, which includes the list of tasks with
                assigned agents.

        Returns:
            The updated state where tasks now contain their execution results.

        Raises:
            ExecutionError: If a critical error occurs during task execution.
        """
        self.logger.info("Executing tasks...")
        self.logger.debug(f"Executing {len(state.tasks)} tasks.")
        try:
            completed_tasks = await self.task_executor.execute_tasks(
                state.tasks, state.user_query
            )

            self.logger.debug(f"Completed {len(completed_tasks)} tasks.")
            state.tasks = completed_tasks
            self.logger.debug("Exiting execute_tasks.")
            return state
        except Exception as e:
            self.logger.exception(f"Error during task execution: {str(e)}")
            raise ExecutionError(f"Error during task execution: {str(e)}") from e

    async def handle_results(self, state: DelegateState) -> DelegateState:
        """Compiles the results of all executed tasks into a final report.

        After all tasks have been executed, this method processes the results. It
        aggregates the outcomes, creates a summary report, and populates the
        final `results` and `report` fields in the state.

        Args:
            state: The state containing the completed tasks with their results.

        Returns:
            The final state with the `results` and `report` attributes populated.
        """
        self.logger.debug("Entering handle_results.")
        if not state.tasks:
            self.logger.info("No tasks were completed successfully.")
            state.results = []
            self.logger.debug("Exiting handle_results with no tasks.")
            return state

        self.logger.info("Task execution completed")
        self.logger.debug(f"Handling results for {len(state.tasks)} completed tasks.")
        state.results = state.tasks
        task_descriptions = [task.description for task in state.tasks]
        state.report = (
            f"Completed {len(state.tasks)} tasks: {', '.join(task_descriptions)}"
        )
        self.logger.debug(f"Generated report: {state.report}")
        self.logger.debug("Exiting handle_results.")
        return state

    def create_error(
        self, state: DelegateState, error_message: str = None
    ) -> DelegateState:
        """Handles an error state by clearing tasks and results.

        This method is called when an unrecoverable error occurs. It resets the
        `tasks` and `results` lists in the state to ensure a clean slate and
        prevent partial or incorrect data from being processed further.

        Args:
            state: The state in which the error occurred.
            error_message: An optional message describing the error.

        Returns:
            The modified state with tasks and results cleared.
        """
        self.logger.debug(f"Entering create_error with message: {error_message}")
        state.results = []
        state.tasks = []
        self.logger.debug("State has been reset due to an error.")
        self.logger.debug("Exiting create_error.")
        return state