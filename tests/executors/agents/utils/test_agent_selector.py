import pytest
from unittest.mock import Mock, patch

from tron_intelligence.executors.agents.utils.agent_selector import AgentSelector
from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.modules.tasks import Task
from tron_intelligence.utils.LLMClient import LLMClient


class TestAgentSelector:
    """Tests for the AgentSelector class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for a mock LLMClient."""
        client = Mock(spec=LLMClient)
        client.call = Mock()
        return client

    @pytest.fixture
    def mock_agents(self):
        """Fixture for a list of mock agents."""
        agents = []
        for i in range(3):
            agent = Mock(spec=Agent)
            agent.name = f"TestAgent{i + 1}"
            agent.description = f"Test agent {i + 1} description"
            agent.full_description = f"Full description for test agent {i + 1}"
            agents.append(agent)
        return agents

    @pytest.fixture
    def mock_tasks(self):
        """Fixture for a list of mock Tasks."""
        tasks = []
        for i in range(3):
            task = Mock(spec=Task)
            task.identifier = f"task{i + 1}"
            task.description = f"Test task {i + 1}"
            task.operations = [f"Operation {i + 1}.{j + 1}" for j in range(2)]
            task.dependencies = []
            task.agent = None
            tasks.append(task)
        return tasks

    @pytest.fixture
    def agent_selector(self, mock_client):
        """Fixture for an AgentSelector instance."""
        return AgentSelector(mock_client)

    @patch("tron_intelligence.executors.agents.utils.agent_selector.build_router_prompt")
    def test_select_agent_success(
        self, mock_build_prompt, agent_selector, mock_client, mock_agents
    ):
        """Test successful agent selection."""
        # Setup
        mock_prompt = Mock()
        mock_build_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.selected_agent = "TestAgent2"  # Second agent in the list
        mock_client.call.return_value = mock_response

        # Act
        result = agent_selector.select_agent("Test query", mock_agents)

        # Assert
        mock_build_prompt.assert_called_once()
        mock_client.call.assert_called_once()
        assert result == mock_agents[1]  # Should be the second agent

    @patch("tron_intelligence.executors.agents.utils.agent_selector.build_router_prompt")
    def test_select_agent_no_match(
        self, mock_build_prompt, agent_selector, mock_client, mock_agents
    ):
        """Test agent selection with no matching agent."""
        # Setup
        mock_prompt = Mock()
        mock_build_prompt.return_value = mock_prompt

        mock_response = Mock()
        mock_response.selected_agent = (
            "NonExistentAgent"  # Agent name that doesn't exist
        )
        mock_client.call.return_value = mock_response

        # Act
        result = agent_selector.select_agent("Test query", mock_agents)

        # Assert
        mock_build_prompt.assert_called_once()
        mock_client.call.assert_called_once()
        assert result is None  # Should not find any matching agent

    @patch("tron_intelligence.executors.agents.utils.agent_selector.build_router_prompt")
    def test_select_agents_all_assigned(
        self, mock_build_prompt, agent_selector, mock_client, mock_agents, mock_tasks
    ):
        """Test task assignment with all tasks assigned to agents."""
        # Setup
        mock_prompt = Mock()
        mock_build_prompt.return_value = mock_prompt

        mock_response = Mock()
        # Format: [(agent_id, task_id), ...]
        mock_response.selected_agents = [
            (("agent", "TestAgent1"), ("task", "task1")),
            (("agent", "TestAgent2"), ("task", "task2")),
            (("agent", "TestAgent3"), ("task", "task3")),
        ]
        mock_client.call.return_value = mock_response

        # Act
        assigned_tasks, unassigned_tasks = agent_selector.select_agents(
            "Test query", mock_tasks, mock_agents
        )

        # Assert
        mock_build_prompt.assert_called_once()
        mock_client.call.assert_called_once()
        assert len(assigned_tasks) == 3
        assert len(unassigned_tasks) == 0

        # Check that tasks were assigned correct agents
        for i, task in enumerate(assigned_tasks):
            assert task.agent == mock_agents[i]

    @patch("tron_intelligence.executors.agents.utils.agent_selector.build_router_prompt")
    def test_select_agents_partial_assignment(
        self, mock_build_prompt, agent_selector, mock_client, mock_agents, mock_tasks
    ):
        """Test task assignment with only some tasks assigned to agents."""
        # Setup
        mock_prompt = Mock()
        mock_build_prompt.return_value = mock_prompt

        mock_response = Mock()
        # Only assign 2 of the 3 tasks
        mock_response.selected_agents = [
            (("agent", "TestAgent1"), ("task", "task1")),
            (("agent", "TestAgent2"), ("task", "task2")),
        ]
        mock_client.call.return_value = mock_response

        # Act
        assigned_tasks, unassigned_tasks = agent_selector.select_agents(
            "Test query", mock_tasks, mock_agents
        )

        # Assert
        mock_build_prompt.assert_called_once()
        mock_client.call.assert_called_once()
        assert len(assigned_tasks) == 2
        # The AgentSelector implementation doesn't automatically detect unassigned tasks
        # It only reports tasks explicitly assigned through the LLM response
        assert len(unassigned_tasks) == 0
        assert assigned_tasks[0].identifier == "task1"
        assert assigned_tasks[1].identifier == "task2"

        # Verify the tasks that were found and assigned
        found_task1 = False
        found_task2 = False
        for task in assigned_tasks:
            if task.identifier == "task1":
                found_task1 = True
                assert task.agent == mock_agents[0]
            if task.identifier == "task2":
                found_task2 = True
                assert task.agent == mock_agents[1]

        assert found_task1
        assert found_task2

    @patch("tron_intelligence.executors.agents.utils.agent_selector.build_router_prompt")
    def test_select_agents_invalid_agent(
        self, mock_build_prompt, agent_selector, mock_client, mock_agents, mock_tasks
    ):
        """Test task assignment with an invalid agent specified."""
        # Setup
        mock_prompt = Mock()
        mock_build_prompt.return_value = mock_prompt

        mock_response = Mock()
        # Include an invalid agent name
        mock_response.selected_agents = [
            (("agent", "NonExistentAgent"), ("task", "task1")),
            (("agent", "TestAgent2"), ("task", "task2")),
        ]
        mock_client.call.return_value = mock_response

        # Act
        assigned_tasks, unassigned_tasks = agent_selector.select_agents(
            "Test query", mock_tasks, mock_agents
        )

        # Assert
        mock_build_prompt.assert_called_once()
        mock_client.call.assert_called_once()
        assert len(assigned_tasks) == 1  # Only one valid assignment
        assert len(unassigned_tasks) == 1  # One task couldn't be assigned
        assert assigned_tasks[0].identifier == "task2"

    @patch("tron_intelligence.executors.agents.utils.agent_selector.build_router_prompt")
    def test_select_agents_no_assignments(
        self, mock_build_prompt, agent_selector, mock_client, mock_agents, mock_tasks
    ):
        """Test task assignment with no valid assignments."""
        # Setup
        mock_prompt = Mock()
        mock_build_prompt.return_value = mock_prompt

        mock_response = Mock()
        # Empty assignments
        mock_response.selected_agents = []
        mock_client.call.return_value = mock_response

        # Act
        assigned_tasks, unassigned_tasks = agent_selector.select_agents(
            "Test query", mock_tasks, mock_agents
        )

        # Assert
        mock_build_prompt.assert_called_once()
        mock_client.call.assert_called_once()
        assert len(assigned_tasks) == 0
        assert (
            len(unassigned_tasks) == 0
        )  # No tasks in unassigned either as we didn't find them
