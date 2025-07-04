from typing import Optional, List, Callable, Awaitable, Dict

import asyncio
from heapq import heappush, heappop
from collections import OrderedDict
import weakref

from tron_ai.modules.tasks.models import Task


class Manager:
    def __init__(
        self, max_completed_tasks: int = 1000, result_size_limit: int = 50 * 1024 * 1024
    ):
        """Initialize TaskManager with performance optimizations.

        Args:
            max_completed_tasks: Maximum number of completed tasks to keep in memory.
                                Older completed tasks will be garbage collected.
            result_size_limit: Maximum total size of task results to keep in memory (bytes).
                              Default is 50MB.
        """
        # Use OrderedDict for O(1) lookups while maintaining insertion order
        self._tasks: OrderedDict[str, Task] = OrderedDict()
        self._execution_order: List[List[Task]] = []

        # Performance optimization: track tasks by state
        self._pending_tasks: Dict[str, weakref.ref] = {}  # Weak refs to pending tasks
        self._completed_tasks: OrderedDict[str, Task] = OrderedDict()

        # Memory management
        self._max_completed_tasks = max_completed_tasks
        self._result_size_limit = result_size_limit
        self._current_result_size = 0

        # Cache for dependency graph
        self._dependency_graph: Optional[Dict[str, List[str]]] = None
        self._in_degree_cache: Optional[Dict[str, int]] = None

    @property
    def tasks(self) -> List[Task]:
        """Return all tasks as a list for backward compatibility."""
        return list(self._tasks.values())

    def add_task(self, task: Task):
        """Register a task with the manager"""
        if task.identifier in self._tasks:
            raise ValueError(f"Duplicate task ID: {task.identifier}")

        self._tasks[task.identifier] = task

        # Add to pending tasks with weak reference
        if not task.done:
            self._pending_tasks[task.identifier] = weakref.ref(task)

        # Invalidate caches
        self._dependency_graph = None
        self._in_degree_cache = None

    def get_dependency_results(self, task: Task) -> dict[str, str]:
        """Get the results of all dependencies for a given task.

        Args:
            task: The task whose dependency results we want to retrieve

        Returns:
            A dictionary mapping dependency task IDs to their results

        Raises:
            ValueError: If any dependency has not completed or failed
        """
        results = {}
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task:
                raise ValueError(f"Dependency task {dep_id} not found")
            if not dep_task.done:
                raise ValueError(f"Dependency task {dep_id} not yet complete")
            if dep_task.error:
                raise ValueError(
                    f"Dependency task {dep_id} failed with error: {dep_task.error}"
                )
            results[dep_id] = dep_task.result
        return results

    def validate_dependencies(self):
        """Check all dependencies exist in the system"""
        all_ids = set(self._tasks.keys())
        for task in self._tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in all_ids:
                    raise ValueError(f"Missing dependency: {dep_id}")

    def prepare_execution_plan(self):
        """Calculate the execution order groups"""
        self.validate_dependencies()
        self._execution_order = self._concurrent_topological_sort()
        return self._execution_order

    async def execute_all(
        self,
        task_handler: Callable[[Task, dict[str, str]], Awaitable[None]],
        concurrency: int = 10,
    ):
        """Execute all tasks with controlled concurrency

        Args:
            task_handler: Async function that takes a task and its dependency results dict
            concurrency: Maximum number of tasks to run concurrently
        """
        if not self._execution_order:
            self.prepare_execution_plan()

        for group in self._execution_order:
            semaphore = asyncio.Semaphore(concurrency)

            async def run_with_semaphore(task):
                async with semaphore:
                    try:
                        # Get dependency results before executing task
                        dep_results = self.get_dependency_results(task)
                        await task_handler(task, dep_results)
                    except Exception as e:
                        task.error = str(e)
                        raise
                    finally:
                        # Mark task as done regardless of outcome
                        task.done = True
                        # Move task to completed and manage memory
                        self._mark_task_completed(task)

            await asyncio.gather(
                *[run_with_semaphore(task) for task in group if not task.done],
                return_exceptions=True
            )

    def _mark_task_completed(self, task: Task):
        """Mark a task as completed and manage memory."""
        if task.identifier in self._pending_tasks:
            del self._pending_tasks[task.identifier]

        if task.done and not task.error:
            self._completed_tasks[task.identifier] = task

            # Estimate result size
            if task.result:
                result_size = len(str(task.result).encode("utf-8"))
                self._current_result_size += result_size

            # Clean up old completed tasks if we exceed limits
            self._cleanup_completed_tasks()

    def _cleanup_completed_tasks(self):
        """Remove old completed tasks to prevent memory growth."""
        # Check task count limit
        while len(self._completed_tasks) > self._max_completed_tasks:
            oldest_id, oldest_task = self._completed_tasks.popitem(last=False)
            if oldest_task.result:
                result_size = len(str(oldest_task.result).encode("utf-8"))
                self._current_result_size -= result_size
            # Clear the result to free memory but keep the task
            oldest_task.result = "<Result cleared for memory optimization>"

        # Check memory size limit
        while (
            self._current_result_size > self._result_size_limit
            and self._completed_tasks
        ):
            oldest_id, oldest_task = self._completed_tasks.popitem(last=False)
            if oldest_task.result:
                result_size = len(str(oldest_task.result).encode("utf-8"))
                self._current_result_size -= result_size
            oldest_task.result = "<Result cleared for memory optimization>"

    def _build_dependency_graph(self) -> tuple[Dict[str, List[str]], Dict[str, int]]:
        """Build and cache the dependency graph."""
        if self._dependency_graph is None or self._in_degree_cache is None:
            self._dependency_graph = {task_id: [] for task_id in self._tasks}
            self._in_degree_cache = {task_id: 0 for task_id in self._tasks}

            for task in self._tasks.values():
                for dep in task.dependencies:
                    self._dependency_graph[dep].append(task.identifier)
                    self._in_degree_cache[task.identifier] += 1

        return self._dependency_graph, self._in_degree_cache

    def _concurrent_topological_sort(self) -> List[List[Task]]:
        """Enhanced Kahn's algorithm implementation with priority queue for parallel groups.

        Returns:
            List[List[Task]]: List of task groups that can be executed in parallel,
                            sorted by priority within each group.

        Raises:
            ValueError: If a circular dependency is detected.
        """
        # Use cached dependency graph
        graph, in_degree = self._build_dependency_graph()

        # Make a copy of in_degree for modification
        in_degree = in_degree.copy()

        # Initialize priority queue with tasks having no dependencies
        # Using negative priority for max-heap behavior (higher priority first)
        current_heap = []
        for task_id, task in self._tasks.items():
            if in_degree[task_id] == 0:
                heappush(current_heap, (-task.priority, task_id, task))

        sorted_groups = []

        while current_heap:
            current_level = []
            next_heap = []

            # Process all tasks at the current priority level
            while current_heap:
                _, _, task = heappop(current_heap)
                current_level.append(task)

                # Update in-degrees and add newly available tasks to next level
                for neighbor_id in graph[task.identifier]:
                    in_degree[neighbor_id] -= 1
                    if in_degree[neighbor_id] == 0:
                        neighbor_task = self._tasks[neighbor_id]
                        heappush(
                            next_heap,
                            (-neighbor_task.priority, neighbor_id, neighbor_task),
                        )

            if current_level:
                sorted_groups.append(current_level)
            current_heap = next_heap

        # Check for circular dependencies
        if sum(len(group) for group in sorted_groups) != len(self._tasks):
            raise ValueError("Circular dependency detected in tasks")

        return sorted_groups

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by its identifier - O(1) lookup"""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")
        return task

    def is_all_complete(self) -> bool:
        """Check if all tasks in the manager are complete."""
        return all(task.done for task in self._tasks.values())

    def get_stats(self) -> dict:
        """Get statistics about the task manager."""
        return {
            "total_tasks": len(self._tasks),
            "pending_tasks": len(self._pending_tasks),
            "completed_tasks": len(self._completed_tasks),
            "memory_usage_mb": self._current_result_size / (1024 * 1024),
            "max_completed_tasks": self._max_completed_tasks,
            "result_size_limit_mb": self._result_size_limit / (1024 * 1024),
        }

    def visualize_dependencies(self) -> str:
        """Generate ASCII tree-style dependency graph"""
        # Build dependency map and find root tasks
        root_tasks = [t for t in self._tasks.values() if not t.dependencies]

        output = ["Task Dependency Graph:\n"]

        def build_branches(task: Task, prefix: str = "", is_last: bool = True):
            """Recursive function to build tree branches"""
            # Current task line
            branch = "└─ " if is_last else "├─ "
            output.append(f"{prefix}{branch}{task.description} ({task.identifier})")

            # Children lines
            new_prefix = prefix + ("   " if is_last else "│  ")
            children = [
                t for t in self._tasks.values() if task.identifier in t.dependencies
            ]

            for i, child in enumerate(children):
                build_branches(child, new_prefix, i == len(children) - 1)

        # Start with root tasks
        for i, task in enumerate(root_tasks):
            build_branches(task, is_last=i == len(root_tasks) - 1)

        # Add orphan detection
        all_shown = set()
        for line in output:
            all_shown.update(
                id for id in line.split() if len(id) == 16 and id.isalnum()
            )

        orphans = [t for t in self._tasks.values() if t.identifier not in all_shown]
        if orphans:
            output.append("\nOrphan Tasks (circular dependencies?):")
            for task in orphans:
                output.append(f"  ⚠ {task.description} ({task.identifier})")

        return "\n".join(output)


if __name__ == "__main__":
    task_manager = Manager()
    task_manager.add_task("Task 1", "This is the first task")
    task_manager.add_task("Task 2", "This is the second task")
    task_manager.add_task("Task 3", "This is the third task")
    asyncio.run(task_manager.run())
