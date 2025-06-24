import pytest
from unittest.mock import Mock, patch

from tron_intelligence.executors.agents.utils.report_generator import ReportGenerator
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.modules.tasks.models import AgentAssignedTask
from tron_intelligence.utils.LLMClient import LLMClient
from tron_intelligence.prompts.models import Prompt


class TestReportGenerator:
    """Tests for the ReportGenerator class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        client = Mock(spec=LLMClient)
        client.call = Mock()
        return client

    @pytest.fixture
    def mock_agent(self):
        """Fixture for a mock Agent."""
        agent = Mock(spec=Agent)
        agent.name = "TestAgent"
        agent.description = "Test agent description"
        return agent

    @pytest.fixture
    def mock_tasks(self, mock_agent):
        """Fixture for mock Tasks with completed results."""
        tasks = []
        for i in range(3):
            task = Mock(spec=AgentAssignedTask)
            task.identifier = f"task{i + 1}"
            task.description = f"Test task {i + 1}"
            task.operations = [f"Operation {i + 1}.{j + 1}" for j in range(2)]
            task.dependencies = []
            task.agent = mock_agent

            # Create mock result
            task.result = Mock()
            task.result.response = f"Result for task {i + 1}"

            # Set task status
            task.done = True
            task.error = None

            tasks.append(task)
        return tasks

    @pytest.fixture
    def mock_tasks_with_failures(self, mock_agent):
        """Fixture for mock Tasks with some failures."""
        tasks = []
        for i in range(3):
            task = Mock(spec=AgentAssignedTask)
            task.identifier = f"task{i + 1}"
            task.description = f"Test task {i + 1}"
            task.operations = [f"Operation {i + 1}.{j + 1}" for j in range(2)]
            task.dependencies = []
            task.agent = mock_agent

            # Set task status
            task.done = True

            # Make one task fail
            if i == 1:
                task.error = "Test error"
                task.result = None
            else:
                task.error = None
                task.result = Mock()
                task.result.response = f"Result for task {i + 1}"

            tasks.append(task)
        return tasks

    @pytest.fixture
    def report_generator(self, mock_client):
        """Fixture for a ReportGenerator instance."""
        return ReportGenerator(mock_client)

    def test_create_task_summaries(self, report_generator, mock_tasks):
        """Test _create_task_summaries method."""
        # Act
        result = report_generator._create_task_summaries(mock_tasks)

        # Assert
        assert len(result) == 3
        for i, summary in enumerate(result):
            assert summary["id"] == f"task{i + 1}"
            assert summary["description"] == f"Test task {i + 1}"
            assert summary["agent"] == "TestAgent"
            assert "result" in summary

    def test_format_task_info(self, report_generator):
        """Test _format_task_info method."""
        # Arrange
        task_summaries = [
            {
                "id": "task1",
                "description": "Test task 1",
                "agent": "TestAgent",
                "dependencies": [],
                "result": "Result for task 1",
            },
            {
                "id": "task2",
                "description": "Test task 2",
                "agent": "TestAgent",
                "dependencies": ["task1"],
                "result": "Result for task 2",
            },
        ]

        # Act
        result = report_generator._format_task_info(task_summaries)

        # Assert
        assert "Task task1:" in result
        assert "Description: Test task 1" in result
        assert "Agent: TestAgent" in result
        assert "Dependencies: None" in result
        assert "Result: Result for task 1" in result

        assert "Task task2:" in result
        assert "Description: Test task 2" in result
        assert "Agent: TestAgent" in result
        assert "Dependencies: task1" in result
        assert "Result: Result for task 2" in result

    def test_create_execution_summary(self, report_generator, mock_tasks):
        """Test _create_execution_summary method."""
        # Act
        result = report_generator._create_execution_summary(mock_tasks)

        # Assert
        assert isinstance(result, list)
        assert "=== Execution Summary ===" in result[0]
        assert "Total Tasks: 3" in result[1]
        assert "Completed: 3" in result[2]
        assert "Failed: 0" in result[3]

        # Check that each task result is included
        task_results_section = "\n".join(result)
        for i in range(3):
            assert f"[task{i + 1}] Test task {i + 1}" in task_results_section
            assert "Agent: TestAgent" in task_results_section
            assert f"Result for task {i + 1}" in task_results_section

    def test_create_execution_summary_with_failures(
        self, report_generator, mock_tasks_with_failures
    ):
        """Test _create_execution_summary method with failed tasks."""
        # Act
        result = report_generator._create_execution_summary(mock_tasks_with_failures)

        # Assert
        assert isinstance(result, list)
        assert "=== Execution Summary ===" in result[0]
        assert "Total Tasks: 3" in result[1]
        assert "Completed: 2" in result[2]
        assert "Failed: 1" in result[3]

        # Only the completed tasks should have their results included
        task_results_section = "\n".join(result)
        assert "[task1] Test task 1" in task_results_section
        assert "Agent: TestAgent" in task_results_section
        assert "Result for task 1" in task_results_section

        assert "[task3] Test task 3" in task_results_section
        assert "Agent: TestAgent" in task_results_section
        assert "Result for task 3" in task_results_section

        # Failed task should not be in the results section
        assert "[task2] Test task 2" not in task_results_section

    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._create_task_summaries"
    )
    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._format_task_info"
    )
    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._generate_detailed_report"
    )
    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._create_execution_summary"
    )
    def test_generate_report(
        self,
        mock_create_summary,
        mock_generate_detailed,
        mock_format_info,
        mock_create_summaries,
        report_generator,
        mock_tasks,
    ):
        """Test generate_report method."""
        # Arrange
        user_query = "Test query"
        mock_task_summaries = [
            {"id": f"task{i}", "description": f"Test {i}"} for i in range(3)
        ]
        mock_create_summaries.return_value = mock_task_summaries

        mock_format_info.return_value = "Formatted task info"

        detailed_report_mock = Mock()
        detailed_report_mock.response = "Detailed report"
        mock_generate_detailed.return_value = detailed_report_mock

        mock_create_summary.return_value = ["Summary line 1", "Summary line 2"]

        # Act
        result = report_generator.generate_report(mock_tasks, user_query)

        # Assert
        mock_create_summaries.assert_called_once_with(mock_tasks)
        mock_format_info.assert_called_once_with(mock_task_summaries)
        mock_generate_detailed.assert_called_once_with(
            "Formatted task info", user_query
        )
        mock_create_summary.assert_called_once_with(mock_tasks)

        assert "Summary line 1\nSummary line 2" in result
        assert "=== Detailed Analysis ===" in result
        assert "Detailed report" in result

    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._create_task_summaries"
    )
    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._format_task_info"
    )
    @patch(
        "tron_intelligence.executors.agents.utils.report_generator.ReportGenerator._create_execution_summary"
    )
    def test_generate_detailed_report(
        self,
        mock_create_summary,
        mock_format_info,
        mock_create_summaries,
        report_generator,
        mock_client,
    ):
        """Test _generate_detailed_report method."""
        # Arrange
        task_info = "Formatted task info"
        user_query = "Test query"

        # Act
        report_generator._generate_detailed_report(task_info, user_query)

        # Assert
        mock_client.call.assert_called_once()
        call_args = mock_client.call.call_args[1]
        assert user_query in call_args["user_query"]
        assert task_info in call_args["user_query"]
        assert "You are an expert at analyzing task execution results." in call_args["system_prompt"].text
