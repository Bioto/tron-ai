"""Tests for the tasks module."""

import pytest
from unittest.mock import Mock
import asyncio

from tron_intelligence.modules.tasks.models import AgentAssignedTask, Task
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.prompts.models import Prompt
from tron_intelligence.modules.tasks import Manager as TaskManager

# Rebuild the Task model to resolve forward references
Task.model_rebuild()


class MockAgent(Agent):
    """Mock implementation of Agent for testing."""

    def __init__(self, name="Test Agent", description="Test Description"):
        super().__init__(
            name=name,
            description=description,
            prompt=Mock(spec=Prompt),
            supports_multiple_operations=True,
        )


class TestTask:
    """Tests for the Task model."""

    def test_task_initialization_defaults(self):
        """Test Task initialization with default values."""
        task = AgentAssignedTask(agent=MockAgent())

        # Check auto-generated identifier
        assert len(task.identifier) == 16
        assert all(c in "0123456789abcdef" for c in task.identifier)

        # Check defaults
        assert task.description == ""
        assert task.operations == []
        assert task.agent is not None
        assert task.dependencies == []
        assert task.result is None
        assert task.error is None
        assert task.done is False
        assert task.priority == 0

    def test_task_initialization_with_values(self):
        """Test Task initialization with custom values."""
        agent = MockAgent()
        task = AgentAssignedTask(
            identifier="custom_id_12345678",
            description="Test task description",
            operations=["op1", "op2"],
            agent=agent,
            dependencies=["dep1", "dep2"],
            priority=5,
        )

        assert task.identifier == "custom_id_12345678"
        assert task.description == "Test task description"
        assert task.operations == ["op1", "op2"]
        assert task.agent == agent
        assert task.dependencies == ["dep1", "dep2"]
        assert task.priority == 5

    def test_task_reset(self):
        """Test Task reset method."""
        task = AgentAssignedTask(agent=MockAgent())
        task.result = "test result"
        task.error = "test error"
        task.done = True

        task.reset()

        assert task.result is None
        assert task.error is None
        assert task.done is False

    def test_task_validation(self):
        """Test Task field validation."""
        # Test description validation (min_length=3)
        with pytest.raises(ValueError):
            AgentAssignedTask(agent=MockAgent(), description="ab")  # Too short


class TestTaskManager:
    """Tests for the TaskManager class."""

    @pytest.fixture
    def task_manager(self):
        """Create a TaskManager instance."""
        return TaskManager()

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        agent1 = MockAgent(name="Agent1")
        agent2 = MockAgent(name="Agent2")

        task1 = AgentAssignedTask(
            identifier="task1",
            description="First task",
            operations=["op1"],
            agent=agent1,
            priority=1,
        )
        task2 = AgentAssignedTask(
            identifier="task2",
            description="Second task",
            operations=["op2"],
            agent=agent2,
            dependencies=["task1"],
            priority=2,
        )
        task3 = AgentAssignedTask(
            identifier="task3",
            description="Third task",
            operations=["op3"],
            agent=agent1,
            dependencies=["task1", "task2"],
            priority=1,
        )
        return [task1, task2, task3]

    def test_add_task(self, task_manager):
        """Test adding tasks to the manager."""
        task = AgentAssignedTask(agent=MockAgent(), identifier="test_task", description="Test task")
        task_manager.add_task(task)

        assert len(task_manager.tasks) == 1
        assert task_manager.tasks[0] == task

    def test_add_duplicate_task(self, task_manager):
        """Test adding duplicate task raises error."""
        task1 = AgentAssignedTask(agent=MockAgent(), identifier="test_task", description="Test task")
        task2 = AgentAssignedTask(agent=MockAgent(), identifier="test_task", description="Another task")

        task_manager.add_task(task1)

        with pytest.raises(ValueError, match="Duplicate task ID: test_task"):
            task_manager.add_task(task2)

    def test_get_task(self, task_manager):
        """Test retrieving a task by ID."""
        task = AgentAssignedTask(agent=MockAgent(), identifier="test_task", description="Test task")
        task_manager.add_task(task)

        retrieved_task = task_manager.get_task("test_task")
        assert retrieved_task == task

    def test_get_task_not_found(self, task_manager):
        """Test retrieving non-existent task raises error."""
        with pytest.raises(KeyError, match="Task not found: non_existent"):
            task_manager.get_task("non_existent")

    def test_get_dependency_results(self, task_manager, sample_tasks):
        """Test getting dependency results."""
        task1, task2, task3 = sample_tasks

        # Mark dependencies as complete
        task1.done = True
        task1.result = "Result 1"
        task2.done = True
        task2.result = "Result 2"

        for task in sample_tasks:
            task_manager.add_task(task)

        # Get dependency results for task3
        results = task_manager.get_dependency_results(task3)

        assert results == {"task1": "Result 1", "task2": "Result 2"}

    def test_get_dependency_results_incomplete(self, task_manager, sample_tasks):
        """Test getting dependency results when dependencies are incomplete."""
        task1, task2, task3 = sample_tasks

        # task1 is complete but task2 is not
        task1.done = True
        task1.result = "Result 1"
        task2.done = False

        for task in sample_tasks:
            task_manager.add_task(task)

        with pytest.raises(ValueError, match="Dependency task task2 not yet complete"):
            task_manager.get_dependency_results(task3)

    def test_get_dependency_results_failed(self, task_manager, sample_tasks):
        """Test getting dependency results when dependency failed."""
        task1, task2, task3 = sample_tasks

        # task1 is complete but task2 failed
        task1.done = True
        task1.result = "Result 1"
        task2.done = True
        task2.error = "Task failed"

        for task in sample_tasks:
            task_manager.add_task(task)

        with pytest.raises(
            ValueError, match="Dependency task task2 failed with error: Task failed"
        ):
            task_manager.get_dependency_results(task3)

    def test_get_dependency_results_missing(self, task_manager):
        """Test getting dependency results when dependency doesn't exist."""
        task = AgentAssignedTask(
            agent=MockAgent(),
            identifier="task1",
            description="Task with missing dependency",
            dependencies=["missing_dep"],
        )
        task_manager.add_task(task)

        with pytest.raises(ValueError, match="Dependency task missing_dep not found"):
            task_manager.get_dependency_results(task)

    def test_validate_dependencies_success(self, task_manager, sample_tasks):
        """Test successful dependency validation."""
        for task in sample_tasks:
            task_manager.add_task(task)

        # Should not raise any exception
        task_manager.validate_dependencies()

    def test_validate_dependencies_missing(self, task_manager):
        """Test dependency validation with missing dependency."""
        task = AgentAssignedTask(
            agent=MockAgent(),
            identifier="task1",
            description="Task with missing dependency",
            dependencies=["missing_dep"],
        )
        task_manager.add_task(task)

        with pytest.raises(ValueError, match="Missing dependency: missing_dep"):
            task_manager.validate_dependencies()

    def test_is_all_complete(self, task_manager, sample_tasks):
        """Test checking if all tasks are complete."""
        for task in sample_tasks:
            task_manager.add_task(task)

        # Initially not all complete
        assert not task_manager.is_all_complete()

        # Mark all as complete
        for task in sample_tasks:
            task.done = True

        assert task_manager.is_all_complete()

    def test_concurrent_topological_sort_simple(self, task_manager):
        """Test concurrent topological sort with simple linear chain."""
        agent = MockAgent()
        task1 = AgentAssignedTask(identifier="task1", agent=agent)
        task2 = AgentAssignedTask(identifier="task2", dependencies=["task1"], agent=agent)
        task3 = AgentAssignedTask(identifier="task3", dependencies=["task2"], agent=agent)

        task_manager.add_task(task1)
        task_manager.add_task(task2)
        task_manager.add_task(task3)

        execution_order = task_manager._concurrent_topological_sort()

        assert len(execution_order) == 3
        assert task1 in execution_order[0]
        assert task2 in execution_order[1]
        assert task3 in execution_order[2]

    def test_concurrent_topological_sort_parallel(self, task_manager):
        """Test concurrent topological sort with parallel tasks."""
        agent = MockAgent()
        task1 = AgentAssignedTask(identifier="task1", agent=agent)
        task2 = AgentAssignedTask(identifier="task2", agent=agent)
        task3 = AgentAssignedTask(
            identifier="task3", dependencies=["task1", "task2"], agent=agent
        )

        task_manager.add_task(task1)
        task_manager.add_task(task2)
        task_manager.add_task(task3)

        execution_order = task_manager._concurrent_topological_sort()

        assert len(execution_order) == 2
        assert task1 in execution_order[0] and task2 in execution_order[0]
        assert task3 in execution_order[1]

    def test_concurrent_topological_sort_priority(self, task_manager):
        """Test concurrent topological sort with priority."""
        agent = MockAgent()
        task1 = AgentAssignedTask(identifier="task1", priority=1, agent=agent)
        task2 = AgentAssignedTask(identifier="task2", priority=2, agent=agent)
        task3 = AgentAssignedTask(
            identifier="task3", dependencies=["task1", "task2"], priority=1, agent=agent
        )

        task_manager.add_task(task1)
        task_manager.add_task(task2)
        task_manager.add_task(task3)

        execution_order = task_manager._concurrent_topological_sort()

        # The first group of tasks should be task2 and task1, sorted by priority.
        # The second group should be task3.
        assert len(execution_order) == 2
        assert len(execution_order[0]) == 2
        assert execution_order[0][0].identifier == "task2"
        assert execution_order[0][1].identifier == "task1"
        assert execution_order[1][0].identifier == "task3"

    def test_concurrent_topological_sort_circular_dependency(self, task_manager):
        """Test that circular dependency raises an error."""
        agent = MockAgent()
        task1 = AgentAssignedTask(identifier="task1", dependencies=["task3"], agent=agent)
        task2 = AgentAssignedTask(identifier="task2", dependencies=["task1"], agent=agent)
        task3 = AgentAssignedTask(identifier="task3", dependencies=["task2"], agent=agent)
        task_manager.add_task(task1)
        task_manager.add_task(task2)
        task_manager.add_task(task3)
    
        with pytest.raises(ValueError, match="Circular dependency detected"):
            task_manager._concurrent_topological_sort()

    def test_prepare_execution_plan(self, task_manager, sample_tasks):
        """Test preparing execution plan."""
        for task in sample_tasks:
            task_manager.add_task(task)

        execution_order = task_manager.prepare_execution_plan()

        assert len(execution_order) > 0
        assert task_manager._execution_order == execution_order

    @pytest.mark.asyncio
    async def test_execute_all_success(self, task_manager, sample_tasks):
        """Test successful execution of all tasks."""
        async def mock_handler(task: AgentAssignedTask, dep_results: dict):
            task.result = f"Result for {task.identifier}"
            task.done = True

        for task in sample_tasks:
            task_manager.add_task(task)

        await task_manager.execute_all(mock_handler)

        for task in task_manager.tasks:
            assert task.done
            assert task.error is None
            assert task.result is not None

        assert task_manager.is_all_complete()

    @pytest.mark.asyncio
    async def test_execute_all_with_error(self, task_manager):
        """Test task execution with an error."""
        agent = MockAgent()
        task1 = AgentAssignedTask(identifier="task1", agent=agent)
        task2 = AgentAssignedTask(identifier="task2", dependencies=["task1"], agent=agent)

        task_manager.add_task(task1)
        task_manager.add_task(task2)

        async def failing_handler(task: AgentAssignedTask, dep_results: dict):
            if task.identifier == "task1":
                raise ValueError("Task failed")
            task.result = "Success"
    
        await task_manager.execute_all(failing_handler)
    
        assert task_manager.get_task("task1").error == "Task failed"
        assert task_manager.get_task("task2").result is None

    @pytest.mark.asyncio
    async def test_execute_all_concurrency_limit(self, task_manager):
        """Test task execution with a concurrency limit."""
        agent = MockAgent()
        tasks = [AgentAssignedTask(identifier=f"task{i}", agent=agent) for i in range(5)]

        for task in tasks:
            task_manager.add_task(task)

        execution_count = 0
        max_concurrent = 0
        currently_executing = 0

        async def counting_handler(task: AgentAssignedTask, dep_results: dict):
            nonlocal execution_count, max_concurrent, currently_executing
            execution_count += 1
            currently_executing += 1
            max_concurrent = max(max_concurrent, currently_executing)
            await asyncio.sleep(0.01)  # Simulate work
            currently_executing -= 1

        await task_manager.execute_all(counting_handler, concurrency=2)

        assert execution_count == 5
        assert max_concurrent == 2

    def test_visualize_dependencies(self, task_manager, sample_tasks):
        """Test dependency visualization."""
        for task in sample_tasks:
            task_manager.add_task(task)

        visualization = task_manager.visualize_dependencies()

        # Check that visualization contains expected elements
        assert "Task Dependency Graph:" in visualization
        assert "First task (task1)" in visualization
        assert "Second task (task2)" in visualization
        assert "Third task (task3)" in visualization
        assert "└─" in visualization or "├─" in visualization

    def test_visualize_dependencies_with_orphans(self, task_manager):
        """Test dependency visualization with orphan tasks."""
        agent = MockAgent()
        task1 = AgentAssignedTask(identifier="task1", agent=agent)
        task2 = AgentAssignedTask(identifier="task2", dependencies=["task1"], agent=agent)
        task3 = AgentAssignedTask(identifier="task3", agent=agent)  # Orphan

        task_manager.add_task(task1)
        task_manager.add_task(task2)
        task_manager.add_task(task3)

        visualization = task_manager.visualize_dependencies()

        assert "task1" in visualization
        assert "task2" in visualization
        assert "task3" in visualization
        assert "orphan" in visualization.lower()
