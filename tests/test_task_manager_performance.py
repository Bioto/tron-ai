"""Test the performance improvements in TaskManager and TaskExecutor."""

import asyncio
import time
import pytest
from unittest.mock import Mock
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tron_intelligence.modules.tasks import Task, AgentAssignedTask, Manager as TaskManager
from tron_intelligence.executors.agents.utils.task_manager import TaskExecutor
from tron_intelligence.executors.agents.models.agent import Agent


class TestTaskManagerPerformance:
    """Test the performance improvements in TaskManager."""

    def test_o1_task_lookup(self):
        """Test that task lookups are O(1) instead of O(n)."""
        manager = TaskManager()

        # Add 1000 tasks
        tasks = []
        for i in range(1000):
            task = Task(
                identifier=f"task_{i}",
                description=f"Task {i}",
                operations=[f"Operation {i}"],
            )
            tasks.append(task)
            manager.add_task(task)

        # Time lookups
        start = time.time()
        for i in range(100):
            # Look up tasks at different positions
            manager.get_task(f"task_{i * 10}")
        lookup_time = time.time() - start

        print(f"\n[Performance] 100 lookups in {lookup_time:.4f}s")
        print(f"[Performance] Average lookup time: {lookup_time / 100 * 1000:.2f}ms")

        # Should be very fast (< 1ms per lookup)
        assert lookup_time < 0.01  # 100 lookups should take < 10ms total

    def test_memory_management(self):
        """Test that completed tasks are cleaned up to prevent memory growth."""
        manager = TaskManager(
            max_completed_tasks=100, result_size_limit=1024 * 1024
        )  # 1MB limit

        # Add and complete many tasks
        for i in range(200):
            task = Task(
                identifier=f"task_{i}",
                description=f"Task {i}",
                operations=[f"Operation {i}"],
            )
            task.done = True
            task.result = "X" * 10000  # 10KB result
            manager.add_task(task)
            manager._mark_task_completed(task)

        stats = manager.get_stats()
        print(f"\n[Memory] Stats after 200 tasks: {stats}")

        # Should have cleaned up old tasks
        assert stats["completed_tasks"] <= 100
        assert stats["memory_usage_mb"] < 1.1  # Should be close to 1MB limit

    def test_dependency_graph_caching(self):
        """Test that dependency graph is cached for performance."""
        manager = TaskManager()

        # Create tasks with dependencies
        for i in range(100):
            task = Task(
                identifier=f"task_{i}",
                description=f"Task {i}",
                dependencies=[f"task_{j}" for j in range(max(0, i - 3), i)],
            )
            manager.add_task(task)

        # First sort should build the cache
        start = time.time()
        manager.prepare_execution_plan()
        first_time = time.time() - start

        # Second sort should use cache (much faster)
        start = time.time()
        manager._concurrent_topological_sort()
        second_time = time.time() - start

        print(f"\n[Cache] First sort: {first_time:.4f}s")
        print(f"[Cache] Second sort (cached): {second_time:.4f}s")
        print(f"[Cache] Speedup: {first_time / second_time:.1f}x")

        # Second sort should be significantly faster
        assert second_time < first_time * 0.5

    def test_duplicate_detection_performance(self):
        """Test that duplicate task detection is O(1)."""
        manager = TaskManager()

        # Add many tasks
        for i in range(1000):
            task = Task(identifier=f"task_{i}", description=f"Task {i}")
            manager.add_task(task)

        # Try to add duplicate (should be fast)
        duplicate = Task(identifier="task_500", description="Duplicate task")

        start = time.time()
        try:
            manager.add_task(duplicate)
        except ValueError as e:
            assert "Duplicate task ID" in str(e)

        detection_time = time.time() - start
        print(f"\n[Duplicate] Detection time: {detection_time * 1000:.2f}ms")

        # Should be very fast (< 1ms)
        assert detection_time < 0.001

    def test_pending_tasks_tracking(self):
        """Test efficient tracking of pending vs completed tasks."""
        manager = TaskManager()

        # Add mix of pending and completed tasks
        for i in range(1000):
            task = Task(
                identifier=f"task_{i}",
                description=f"Task {i}",
                done=i % 2 == 0,  # Half are done
            )
            manager.add_task(task)

        # Check completion should be O(1)
        start = time.time()
        for _ in range(100):
            is_complete = manager.is_all_complete()
        check_time = time.time() - start

        print(f"\n[Completion] 100 checks in {check_time * 1000:.2f}ms")
        assert not is_complete  # Should have pending tasks
        assert check_time < 0.001  # Should be very fast

    @pytest.mark.asyncio
    async def test_concurrent_execution_performance(self):
        """Test performance with many concurrent tasks."""
        # Mock client and config
        mock_client = Mock()
        # Create an async mock for fcall that returns a proper response
        async def mock_fcall(*args, **kwargs):
            # Return a simple object with response attribute
            result = Mock()
            result.response = "Result"
            return result
        
        mock_client.fcall = mock_fcall
        mock_config = Mock()

        executor = TaskExecutor(mock_client, mock_config)

        # Create many independent tasks (can run concurrently)
        tasks = []
        for i in range(50):
            # Create a proper agent mock without __rich_repr__
            agent = Mock(spec=Agent)
            agent.name = f"Agent{i}"
            agent.prompt = "Test prompt"
            agent.tools = None
            agent.tool_manager = None
            # Remove any __rich_repr__ method that might be auto-created
            if hasattr(agent, '__rich_repr__'):
                delattr(agent, '__rich_repr__')

            task = AgentAssignedTask(
                identifier=f"task_{i}",
                description=f"Task {i}",
                operations=[f"Op{i}"],
                agent=agent,
            )
            tasks.append(task)

        # Execute with concurrency
        start = time.time()
        completed = await executor.execute_tasks(tasks, "Test query")
        execution_time = time.time() - start

        print(
            f"\n[Concurrent] Executed {len(completed)} tasks in {execution_time:.2f}s"
        )
        print(
            f"[Concurrent] Average per task: {execution_time / len(completed) * 1000:.2f}ms"
        )

        # Check all completed successfully
        assert len(completed) == 50
        assert all(t.done and not t.error for t in completed)

    def test_result_size_tracking(self):
        """Test accurate tracking of result sizes."""
        manager = TaskManager(result_size_limit=1024 * 1024)  # 1MB

        # Add tasks with known result sizes
        total_size = 0
        for i in range(10):
            task = Task(identifier=f"task_{i}", description=f"Task {i}")
            task.done = True
            # Create result of specific size
            task.result = "A" * (100 * 1024)  # 100KB
            total_size += len(task.result.encode("utf-8"))

            manager.add_task(task)
            manager._mark_task_completed(task)

        stats = manager.get_stats()
        print(f"\n[Size] Expected size: {total_size / 1024 / 1024:.2f}MB")
        print(f"[Size] Tracked size: {stats['memory_usage_mb']:.2f}MB")

        # Should track size accurately
        assert abs(stats["memory_usage_mb"] - total_size / 1024 / 1024) < 0.01


def benchmark_task_manager():
    """Run benchmarks comparing old vs new implementation."""
    print("\n" + "=" * 60)
    print("TaskManager Performance Benchmark")
    print("=" * 60)

    # Benchmark task creation and lookup
    manager = TaskManager()

    # Add tasks
    start = time.time()
    for i in range(10000):
        task = Task(
            identifier=f"task_{i}", description=f"Task {i}", operations=[f"Op{i}"]
        )
        manager.add_task(task)
    add_time = time.time() - start
    print(f"\nAdded 10,000 tasks in {add_time:.2f}s ({10000 / add_time:.0f} tasks/sec)")

    # Lookup tasks
    start = time.time()
    for i in range(0, 10000, 100):
        manager.get_task(f"task_{i}")
    lookup_time = time.time() - start
    print(
        f"100 lookups in {lookup_time * 1000:.2f}ms (avg {lookup_time / 100 * 1000:.3f}ms)"
    )

    # Dependency resolution
    start = time.time()
    manager.prepare_execution_plan()
    sort_time = time.time() - start
    print(f"Dependency sort in {sort_time:.2f}s")

    # Memory stats
    stats = manager.get_stats()
    print("\nMemory stats:")
    print(f"  Total tasks: {stats['total_tasks']}")
    print(f"  Memory usage: {stats['memory_usage_mb']:.2f}MB")
    print(
        f"  Limits: {stats['max_completed_tasks']} tasks, {stats['result_size_limit_mb']:.0f}MB"
    )


if __name__ == "__main__":
    # Run the benchmark
    benchmark_task_manager()

    # Run the tests
    test = TestTaskManagerPerformance()
    test.test_o1_task_lookup()
    test.test_memory_management()
    test.test_dependency_graph_caching()
    test.test_duplicate_detection_performance()
    test.test_pending_tasks_tracking()
    test.test_result_size_tracking()

    # Run async test
    asyncio.run(test.test_concurrent_execution_performance())

    print("\n✅ All performance tests passed!")
