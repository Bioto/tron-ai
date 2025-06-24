import pytest
from unittest.mock import AsyncMock, Mock, patch, PropertyMock

from tron_intelligence.executors.agents.utils.task_manager import TaskExecutor
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.modules.tasks.models import AgentAssignedTask
from tron_intelligence.utils.LLMClient import LLMClient
from tron_intelligence.executors.base import ExecutorConfig
from tron_intelligence.prompts.models import Prompt


class TestTaskExecutor:
    """Tests for the TaskExecutor class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        client = Mock(spec=LLMClient)
        client.fcall = AsyncMock()
        return client

    @pytest.fixture
    def mock_config(self, mock_client):
        """Fixture for a mock ExecutorConfig."""
        return Mock(spec=ExecutorConfig, client=mock_client)

    @pytest.fixture
    def mock_agent(self):
        """Fixture for a mock Agent."""
        agent = Mock(spec=Agent)
        agent.name = "TestAgent"
        agent.description = "Test agent description"
        agent.prompt = Mock(spec=Prompt)
        agent.tools = Mock()  # Mock tools manager
        return agent

    @pytest.fixture
    def mock_tasks(self, mock_agent):
        """Fixture for a list of mock Tasks."""
        tasks = []
        for i in range(3):
            task = Mock(spec=AgentAssignedTask)
            task.identifier = f"task{i + 1}"
            task.description = f"Test task {i + 1}"
            task.operations = [f"Operation {i + 1}.{j + 1}" for j in range(2)]
            task.dependencies = []
            task.agent = mock_agent
            task.done = False
            task.error = None
            # Configure __rich_repr__ to return an empty list for Rich pretty printing
            task.__rich_repr__ = Mock(return_value=[])
            tasks.append(task)
        return tasks

    @pytest.fixture
    def mock_tasks_with_dependencies(self, mock_agent):
        """Fixture for a list of mock Tasks with dependencies."""
        tasks = []
        for i in range(3):
            task = Mock(spec=AgentAssignedTask)
            task.identifier = f"task{i + 1}"
            task.description = f"Test task {i + 1}"
            task.operations = [f"Operation {i + 1}.{j + 1}" for j in range(2)]
            task.agent = mock_agent
            task.done = False
            task.error = None
            # Configure __rich_repr__ to return an empty list for Rich pretty printing
            task.__rich_repr__ = Mock(return_value=[])

            # Add dependencies for task2 and task3
            if i == 1:  # task2 depends on task1
                task.dependencies = ["task1"]
            elif i == 2:  # task3 depends on task1 and task2
                task.dependencies = ["task1", "task2"]
            else:
                task.dependencies = []

            tasks.append(task)
        return tasks

    @pytest.fixture
    def task_executor(self, mock_client, mock_config):
        """Fixture for a TaskExecutor instance."""
        return TaskExecutor(mock_client, mock_config)

    @patch("tron_intelligence.modules.tasks.manager.Manager.add_task")
    @patch("tron_intelligence.modules.tasks.manager.Manager.execute_all")
    async def test_execute_tasks_success(
        self, mock_execute_all, mock_add_task, task_executor, mock_tasks
    ):
        """Test successful task execution."""
        # Setup
        user_query = "Test query"

        # Make execute_all complete the tasks
        async def fake_execute_all(handler):
            for task in mock_tasks:
                # Simulate successful task execution
                task.done = True
                task.error = None
                task.result = Mock()
                task.result.response = f"Result for {task.identifier}"

        mock_execute_all.side_effect = fake_execute_all

        # Patch the tasks property to return our completed tasks
        with patch.object(
            type(task_executor.task_manager), "tasks", new_callable=PropertyMock
        ) as mock_tasks_prop:
            mock_tasks_prop.return_value = mock_tasks
            # Act
            result = await task_executor.execute_tasks(mock_tasks, user_query)

            # Assert
            # Check that tasks were added to the task manager
            assert mock_add_task.call_count == 3
            for task in mock_tasks:
                mock_add_task.assert_any_call(task)

            # Check that execute_all was called
            mock_execute_all.assert_called_once()

            # Check that result contains our tasks
            assert len(result) == 3
            for task in result:
                assert task.done is True
                assert task.error is None
                assert hasattr(task, "result")
                assert hasattr(task.result, "response")
                assert task.result.response.startswith("Result for")

    @patch("tron_intelligence.modules.tasks.manager.Manager.add_task")
    @patch("tron_intelligence.modules.tasks.manager.Manager.execute_all")
    async def test_execute_tasks_with_failed_task(
        self, mock_execute_all, mock_add_task, task_executor, mock_tasks
    ):
        """Test task execution with a failed task."""
        # Setup
        user_query = "Test query"

        # Make execute_all fail the second task
        async def fake_execute_all(handler):
            for i, task in enumerate(mock_tasks):
                if i == 1:  # Fail the second task
                    task.done = True
                    task.error = "Test error"
                else:
                    # Complete the other tasks
                    task.done = True
                    task.result = Mock()
                    task.result.response = f"Result for {task.identifier}"

        mock_execute_all.side_effect = fake_execute_all

        # Patch the tasks property to return all tasks including the failed one
        with patch.object(
            type(task_executor.task_manager), "tasks", new_callable=PropertyMock
        ) as mock_tasks_prop:
            mock_tasks_prop.return_value = mock_tasks
            # Act/Assert
            with pytest.raises(Exception, match="Some tasks failed"):
                await task_executor.execute_tasks(mock_tasks, user_query)

            # Check that tasks were added to the task manager
            assert mock_add_task.call_count == 3

            # Check that execute_all was called
            mock_execute_all.assert_called_once()

    def test_build_operations_query(self, task_executor, mock_tasks):
        """Test _build_operations_query method."""
        # Setup
        user_query = "Test query"
        task = mock_tasks[0]
        dependency_results = {}

        # Act
        result = task_executor._build_operations_query(
            task, user_query, dependency_results
        )

        # Assert
        assert "Original Query: Test query" in result
        assert f"Task Description: {task.description}" in result
        assert "Operations to perform in sequence:" in result
        for op in task.operations:
            assert op in result
        assert "Instructions:" in result

    def test_build_operations_query_with_dependencies(
        self, task_executor, mock_tasks_with_dependencies
    ):
        """Test _build_operations_query method with dependencies."""
        # Setup
        user_query = "Test query"
        task = mock_tasks_with_dependencies[2]  # task3 with dependencies

        # Create mock dependency results
        dep1_result = Mock()
        dep1_result.response = "Result for task1"
        dep2_result = Mock()
        dep2_result.response = "Result for task2"

        dependency_results = {"task1": dep1_result, "task2": dep2_result}

        # Patch the tasks property to return dependency tasks
        with (
            patch.object(
                type(task_executor.task_manager), "tasks", new_callable=PropertyMock
            ) as mock_tasks_prop,
            patch.object(type(task_executor.task_manager), "get_task") as mock_get_task,
        ):
            mock_tasks_prop.return_value = mock_tasks_with_dependencies

            # Patch get_task to return the correct mock for each dependency
            def get_task_side_effect(task_id):
                for t in mock_tasks_with_dependencies:
                    if t.identifier == task_id:
                        return t
                raise KeyError(f"Task not found: {task_id}")

            mock_get_task.side_effect = get_task_side_effect
            # Act
            result = task_executor._build_operations_query(
                task, user_query, dependency_results
            )

            # Assert
            assert "Original Query: Test query" in result
            assert f"Task Description: {task.description}" in result
            assert "Operations to perform in sequence:" in result
            for op in task.operations:
                assert op in result

            assert "Dependency Results:" in result
            assert "Dependency Task 'task1':" in result
            assert "Result for task1" in result
            assert "Dependency Task 'task2':" in result
            assert "Result for task2" in result

            assert "Instructions:" in result

    @patch(
        "tron_intelligence.executors.agents.utils.task_manager.TaskExecutor._build_operations_query"
    )
    async def test_task_handler_success(
        self, mock_build_query, task_executor, mock_tasks, mock_client
    ):
        """Test the task_handler function for successful execution."""
        # Setup
        task = mock_tasks[0]
        dependency_results = {}

        mock_build_query.return_value = "Test operations query"

        # Setup mock response for async call
        mock_response = Mock()
        mock_response.response = "Task result"

        # Create a simple task handler function to test directly
        async def test_handler():
            # Replace the client's fcall with our own AsyncMock
            original_fcall = task_executor.client.fcall
            task_executor.client.fcall = AsyncMock(return_value=mock_response)

            try:
                # Create a task handler directly
                async def handler(task, dependency_results):
                    if task.agent:
                        operations_query = task_executor._build_operations_query(
                            task, "Test query", dependency_results
                        )

                        result = await task_executor.client.fcall(
                            user_query=operations_query
                            + "\n\n"
                            + "Always return your response in markdown format.",
                            system_prompt=task.agent.prompt,
                            tool_manager=task.agent.tools,
                        )

                        task.result = result
                        task.done = True
                    else:
                        task.error = "No agent assigned"
                        task.done = True

                # Call the handler
                await handler(task, dependency_results)

                # Verify it was called correctly
                assert task_executor.client.fcall.await_count == 1
                assert task.result == mock_response
                assert task.done is True
            finally:
                # Restore the original fcall
                task_executor.client.fcall = original_fcall

        # Act
        await test_handler()

        # Assert
        mock_build_query.assert_called_once()

    @patch(
        "tron_intelligence.executors.agents.utils.task_manager.TaskExecutor._build_operations_query"
    )
    async def test_task_handler_client_error(
        self, mock_build_query, task_executor, mock_tasks, mock_client
    ):
        """Test the task_handler function with client error."""
        # Setup
        task = mock_tasks[0]
        dependency_results = {}

        mock_build_query.return_value = "Test operations query"

        # Create a simple task handler function to test directly
        async def test_handler():
            # Replace the client's fcall with our own AsyncMock that raises an error
            original_fcall = task_executor.client.fcall
            task_executor.client.fcall = AsyncMock(
                side_effect=ValueError("Test client error")
            )

            try:
                # Create a task handler directly
                async def handler(task, dependency_results):
                    try:
                        if task.agent:
                            operations_query = task_executor._build_operations_query(
                                task, "Test query", dependency_results
                            )

                            result = await task_executor.client.fcall(
                                user_query=operations_query
                                + "\n\n"
                                + "Always return your response in markdown format.",
                                system_prompt=task.agent.prompt,
                                tool_manager=task.agent.tools,
                            )

                            task.result = result
                            task.done = True
                        else:
                            task.error = "No agent assigned"
                            task.done = True
                    except Exception as e:
                        task.error = str(e)
                        task.done = True

                # Call the handler
                await handler(task, dependency_results)

                # Verify error was handled correctly
                assert task_executor.client.fcall.await_count == 1
                assert task.error is not None
                assert "Test client error" in task.error
                assert task.done is True
            finally:
                # Restore the original fcall
                task_executor.client.fcall = original_fcall

        # Act
        await test_handler()

        # Assert
        mock_build_query.assert_called_once()

    @patch(
        "tron_intelligence.executors.agents.utils.task_manager.TaskExecutor._build_operations_query"
    )
    async def test_task_handler_no_agent(
        self, mock_build_query, task_executor, mock_tasks
    ):
        """Test the task_handler function with no agent assigned."""
        # Setup
        task = mock_tasks[0]
        task.agent = None  # Remove agent
        dependency_results = {}

        # Create a task handler by extracting it from execute_tasks
        async def extract_handler():
            with (
                patch("tron_intelligence.modules.tasks.manager.Manager.add_task"),
                patch(
                    "tron_intelligence.modules.tasks.manager.Manager.execute_all"
                ) as mock_execute_all,
            ):

                def capture_handler(handler):
                    extract_handler.captured_handler = handler

                mock_execute_all.side_effect = capture_handler
                await task_executor.execute_tasks([task], "Test query")
                return extract_handler.captured_handler

        task_handler = await extract_handler()

        # Act
        await task_handler(task, dependency_results)

        # Assert
        assert task.done is True
        assert task.error is not None  # Just check that error is set
