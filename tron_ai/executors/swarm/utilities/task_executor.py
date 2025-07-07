from typing import List
import asyncio
from tron_ai.constants import TIMEOUT_TASK_EXECUTION
from tron_ai.modules.tasks import Task, Manager
from tron_ai.utils.llm.LLMClient import LLMClient
from tron_ai.exceptions import (
    TaskError,
    TimeoutError as TronTimeoutError,
    AgentError,
)
from tron_ai.database.manager import DatabaseManager
from tron_ai.database.config import DatabaseConfig

import logging
import types


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

    async def execute_tasks(self, tasks: List[Task], user_query: str, session_id: str = None, root_id: str = None) -> List[Task]:
        """Executes a list of tasks, handling dependencies and parallelism.

        This is the main entry point for the executor. It adds all tasks to the
        task manager, which builds a dependency graph. It then executes the tasks
        in an order that respects these dependencies, running tasks that can be

        Args:
            tasks: A list of `Task` objects to be executed.
            user_query: The original user query to provide context for task execution.
            session_id: The ID of the workflow associated with the task execution.
            root_id: The ID of the root task associated with the task execution.

        Returns:
            A list of the `Task` objects that were completed successfully.

        Raises:
            TaskError: If one or more tasks fail during execution.
        """
        db_manager = None
        if session_id:
            db_config = DatabaseConfig()
            db_manager = DatabaseManager(db_config)
            await db_manager.initialize()

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
                            self.logger.debug(f"Calling agent '{task.agent.name}' for task '{task.identifier}'")

                            result = self.client.fcall(
                                user_query=operations_query + "\n\n"+ "Always return your response in markdown format.\n\nIMPORTANT: When displaying email snippets or any content retrieved from APIs, ALWAYS show the COMPLETE text. NEVER truncate, shorten, or add phrases like '[truncated for brevity]' or similar. Display all content in full.",
                                system_prompt=task.agent.prompt,
                                tool_manager=task.agent.tool_manager,
                            )

                            task.result = result
                            
                            # Log the actual result content
                            if hasattr(result, 'response'):
                                self.logger.info(f"Task '{task.identifier}' result length: {len(result.response)} characters")
                                self.logger.debug(f"Task '{task.identifier}' full result: {result.response[:500]}..." if len(result.response) > 500 else f"Task '{task.identifier}' full result: {result.response}")
                            else:
                                self.logger.info(f"Task '{task.identifier}' result type: {type(result)}")
                                self.logger.debug(f"Task '{task.identifier}' result: {str(result)[:500]}...")
                            
                            self.logger.info(
                                f"Task '{task.identifier}' completed successfully"
                            )
                            # --- Database logging for agent-to-agent messages ---
                            if db_manager:
                                # Only log tool_calls if result is not a router/orchestrator result and not just the known error
                                tool_calls_to_log = None
                                # Check if the result actually has tool_calls before trying to access it
                                try:
                                    if hasattr(result, 'tool_calls') and result.tool_calls:
                                        # Defensive: skip if result is a known router/orchestrator type or just the known error
                                        router_types = (str,)
                                        is_router_type = hasattr(result, '__class__') and result.__class__.__name__ in ["AgentRouterResults", "SwarmResults"]
                                        # Check for the specific error pattern
                                        is_only_router_error = (
                                            len(result.tool_calls) == 1 and
                                            result.tool_calls[0].get('name') == 'execute_on_swarm' and
                                            'AgentRouterResults' in str(result.tool_calls[0].get('error', ''))
                                        )
                                        if not is_router_type and not is_only_router_error:
                                            tool_calls_to_log = result.tool_calls
                                except AttributeError:
                                    # If we get an AttributeError when accessing tool_calls, just skip it
                                    self.logger.debug(f"Result type {type(result).__name__} does not have tool_calls field")
                                    tool_calls_to_log = None
                                await db_manager.add_message(
                                    session_id=session_id,
                                    role="agent",
                                    content=operations_query,
                                    agent_name=task.agent.name,
                                    meta={
                                        "task_id": task.identifier,
                                        "task_description": task.description,
                                        "operations": task.operations,
                                        "dependencies": task.dependencies,
                                        "root_id": root_id,
                                    },
                                    task_id=task.identifier,
                                    root_id=root_id,
                                )
                                # Prepare content for assistant message
                                content = getattr(result, 'response', None)
                                if not content:
                                    content = str(result) if result is not None else ""
                                # Only log assistant message if content is not empty
                                if content:
                                    await db_manager.add_message(
                                        session_id=session_id,
                                        role="assistant",
                                        content=content,
                                        agent_name=task.agent.name,
                                        tool_calls=tool_calls_to_log,
                                        meta={
                                            "task_id": task.identifier,
                                            "task_description": task.description,
                                            "operations": task.operations,
                                            "dependencies": task.dependencies,
                                            "result_type": str(type(result)),
                                            "root_id": root_id,
                                        },
                                        task_id=task.identifier,
                                        root_id=root_id,
                                    )
                                await db_manager.add_agent_session(
                                    session_id=session_id,
                                    agent_name=task.agent.name,
                                    user_query=operations_query,
                                    agent_response=getattr(result, 'response', str(result)),
                                    tool_calls=tool_calls_to_log,
                                    execution_time_ms=None,
                                    success=True,
                                    error_message=None,
                                    meta={
                                        "task_id": task.identifier,
                                        "task_description": task.description,
                                        "operations": task.operations,
                                        "dependencies": task.dependencies,
                                        "root_id": root_id,
                                    }
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

        # At the end, close db_manager if used
        if db_manager:
            await db_manager.close()

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
