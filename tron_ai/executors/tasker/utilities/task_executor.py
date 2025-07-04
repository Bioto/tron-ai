from typing import List
import asyncio
from tron_ai.constants import TIMEOUT_TASK_EXECUTION
from tron_ai.modules.tasks import Task, Manager
from tron_ai.utils.LLMClient import LLMClient
from tron_ai.exceptions import (
    TaskError,
    TimeoutError as TronTimeoutError,
    AgentError,
)

import logging


class TaskExecutor:
    """Handles the execution of a list of tasks with dependency management and parallelism.

    This class is responsible for taking a set of tasks, respecting their
    dependencies, and executing them efficiently. It uses a `Manager` to handle
    the task graph and `asyncio` to run independent tasks concurrently. It also
    manages timeouts, error handling, and resource limits (memory).
    """

    def __init__(
        self,
        client: LLMClient,
        max_completed_tasks: int = 1000,
        result_size_limit_mb: int = 50,
    ):
        """Initializes the TaskExecutor with resource management settings.

        Args:
            client: The LLMClient instance used to execute task operations.
            max_completed_tasks: The maximum number of completed tasks to retain
                in memory, preventing unbounded growth.
            result_size_limit_mb: The total size limit in megabytes for all
                stored task results to prevent excessive memory usage.
        """
        self.client = client
        # Initialize TaskManager with memory limits
        self.task_manager = Manager(
            max_completed_tasks=max_completed_tasks,
            result_size_limit=result_size_limit_mb * 1024 * 1024,
        )
        self.logger = logging.getLogger(__name__)

    async def execute_tasks(self, tasks: List[Task], user_query: str) -> List[Task]:
        """Executes a list of tasks, handling dependencies and parallelism.

        This is the main entry point for the executor. It adds all tasks to the
        task manager, which builds a dependency graph. It then executes the tasks
        in an order that respects these dependencies, running tasks that can be

        Args:
            tasks: A list of `Task` objects to be executed.
            user_query: The original user query to provide context for task execution.

        Returns:
            A list of the `Task` objects that were completed successfully.

        Raises:
            TaskError: If one or more tasks fail during execution.
        """

        async def task_handler(task: Task, dependency_results: dict[str, str]):
            try:
                if hasattr(task, "agent") and task.agent:
                    self.logger.info(
                        f"Executing task '{task.identifier}' with agent '{task.agent.name}'"
                    )
                    if dependency_results:
                        self.logger.info(
                            f"Task has {len(dependency_results)} dependencies"
                        )

                    # Build operation-specific query
                    operations_query = self._build_operations_query(
                        task, user_query, dependency_results
                    )

                    try:
                        async with asyncio.timeout(
                            TIMEOUT_TASK_EXECUTION  
                        ):  # Increased timeout for multiple operations
                            self.logger.info(
                                f"Calling agent for task '{task.identifier}' with {len(task.operations)} operations"
                            )

                            result = self.client.fcall(
                                user_query=operations_query
                                + "\n\n"
                                + "Always return your response in markdown format.",
                                system_prompt=task.agent.prompt,
                                tool_manager=task.agent.tool_manager,
                            )

                            task.result = result
                            self.logger.info(
                                f"Task '{task.identifier}' completed successfully"
                            )
                    except asyncio.TimeoutError:
                        error_msg = f"Task execution timed out after {TIMEOUT_TASK_EXECUTION} seconds"
                        self.logger.info(f"Error: {error_msg}")
                        raise TronTimeoutError(
                            error_msg,
                            timeout=TIMEOUT_TASK_EXECUTION,
                            operation=f"task_{task.identifier}"
                        )
                    except Exception as e:
                        self.logger.exception(
                            f"Task '{task.identifier}' failed: {str(e)}"
                        )
                        raise TaskError(
                            f"Task execution failed: {str(e)}",
                            context={
                                "task_id": task.identifier,
                                "task_description": task.description,
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                        )
                else:
                    error_msg = f"No agent assigned to task: {task.identifier}"
                    self.logger.debug(f"Error: {error_msg}")
                    raise AgentError(
                        error_msg,
                        context={
                            "task_id": task.identifier,
                            "task_description": task.description
                        }
                    )

                task.done = True
            except Exception as e:
                self.logger.exception(f"Task '{task.identifier}' failed: {str(e)}")
                task.error = str(e)
                task.done = True

        # Add tasks to manager
        for task in tasks:
            self.task_manager.add_task(task)
            self.logger.info(
                f"Added task: '{task.identifier}': {task.description} with {len(task.operations)} operations"
            )

        # Log memory stats before execution
        stats = self.task_manager.get_stats()
        self.logger.info(
            f"TaskManager stats before execution: "
            f"total={stats['total_tasks']}, "
            f"pending={stats['pending_tasks']}, "
            f"memory_mb={stats['memory_usage_mb']:.2f}"
        )

        # Execute all tasks
        self.logger.info("Starting task execution")
        await self.task_manager.execute_all(task_handler)
        self.logger.info("Task execution completed")

        # Log memory stats after execution
        stats = self.task_manager.get_stats()
        self.logger.info(
            f"TaskManager stats after execution: "
            f"total={stats['total_tasks']}, "
            f"completed={stats['completed_tasks']}, "
            f"memory_mb={stats['memory_usage_mb']:.2f}"
        )

        # Check for failed tasks
        failed_tasks = [t for t in self.task_manager.tasks if t.error]
        if failed_tasks:
            error_details = []
            for t in failed_tasks:
                error_details.append({
                    "task_id": t.identifier,
                    "description": t.description,
                    "error": t.error
                })
                
            raise TaskError(
                f"Some tasks failed during execution: {len(failed_tasks)}",
                context={
                    "failed_count": len(failed_tasks),
                    "total_tasks": len(self.task_manager.tasks),
                    "failed_tasks": error_details
                }
            )

        completed_tasks = [t for t in self.task_manager.tasks if t.done and not t.error]
        self.logger.info(f"Successfully completed {len(completed_tasks)} tasks")
        return completed_tasks

    def _build_operations_query(
        self, task: Task, user_query: str, dependency_results: dict[str, str]
    ) -> str:
        """Constructs the detailed prompt for an agent to execute a task.

        This method assembles a comprehensive prompt that includes the original
        query, the specific task description, a list of operations, and the
        results from any prerequisite tasks. This gives the agent all the context
        it needs to perform its work accurately.

        Args:
            task: The `Task` to be executed.
            user_query: The original user query.
            dependency_results: A dictionary mapping dependency task IDs to their
                results.

        Returns:
            A formatted string containing the full prompt for the agent.
        """
        operations_list = "\n".join(
            f"{i + 1}. {op}" for i, op in enumerate(task.operations)
        )

        query_parts = [
            f"Original Query: {user_query}\n",
            f"Task Description: {task.description}\n",
            f"\nOperations to perform in sequence:\n{operations_list}\n",
        ]
        if dependency_results:
            dep_sections = []
            for dep_id, result in dependency_results.items():
                # Use optimized get_task method (O(1) lookup)
                try:
                    dep_task = self.task_manager.get_task(dep_id)
                    dep_sections.append(
                        f"Dependency Task '{dep_id}':"
                        f"\n- Description: {dep_task.description}"
                        f"\n- Result:\n{result.response}\n"
                    )
                except KeyError:
                    # Task not found, skip
                    pass
            if dep_sections:
                query_parts.append("\nDependency Results:\n" + "\n".join(dep_sections))

        query_parts.append(
            "\nInstructions:"
            "\n1. Execute each operation in the specified sequence"
            "\n2. Use appropriate tools for each operation"
            "\n3. Provide results after each operation"
            "\n4. Handle any errors that occur during execution"
            "\n5. Return a combined summary of all operations"
            "\n6. IMPORTANT: Avoid making duplicate or redundant tool calls"
            "\n7. IMPORTANT: Do not scrape the same URL multiple times"
            "\n8. If you need data from a previously scraped URL, use the data already obtained"
            "\n9. Consolidate operations to minimize the number of tool calls"
        )

        return "\n".join(query_parts)

    def get_stats(self) -> dict:
        """Retrieves execution statistics from the underlying task manager.

        Returns:
            A dictionary containing statistics like total tasks, pending tasks,
            completed tasks, and memory usage.
        """
        return self.task_manager.get_stats()
