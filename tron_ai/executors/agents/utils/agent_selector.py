from typing import List, Tuple, Optional, Sequence
from tron_ai.executors.agents.models.agent import Agent
from tron_ai.executors.agents.prompts.agent_router_prompt import build_router_prompt
from tron_ai.utils.LLMClient import LLMClient
from tron_ai.modules.tasks import Task
from tron_ai.modules.tasks.models import AgentAssignedTask

import logging

logger = logging.getLogger(__name__)


class AgentSelector:
    """A utility for selecting the most appropriate agent(s) for a given task or query.

    This class uses an LLM to route requests to the best-suited agent from a
    provided list. It can either select a single agent for a simple query or
    assign multiple agents to a list of tasks.
    """

    def __init__(self, client: LLMClient):
        """Initializes the AgentSelector.

        Args:
            client: An instance of LLMClient to interact with the language model.
        """
        self.client = client

    def select_agent(self, user_query: str, agents: Sequence[Agent]) -> Optional[Agent]:
        """Selects the single most appropriate agent for a given user query.

        This method is suitable for single-step tasks where one agent is expected
        to handle the entire query.

        Args:
            user_query: The user's input query.
            agents: A sequence of available `Agent` objects to choose from.

        Returns:
            The selected `Agent` object, or `None` if no suitable agent is found.
        """
        router_prompt = build_router_prompt()
        agent_info = [(agent.name, agent.description) for agent in agents]

        response = self.client.call(
            user_query=user_query,
            system_prompt=router_prompt,
            prompt_kwargs={"agents": agent_info},
        )

        selected_agent = response.selected_agent
        return next((agent for agent in agents if agent.name == selected_agent), None)

    def select_agents(
        self, user_query: str, tasks: List[Task], agents: Sequence[Agent]
    ) -> Tuple[List[AgentAssignedTask], List[Task]]:
        """Assigns the most appropriate agent to each task in a list.

        This method uses an LLM to evaluate a list of tasks against a list of
        available agents and determines the best agent for each task. It is
        the core of the task delegation logic.

        Args:
            user_query: The original user query that led to the tasks.
            tasks: A list of `Task` objects to be assigned.
            agents: A sequence of `Agent` objects available for assignment.

        Returns:
            A tuple containing two lists:
            - A list of `AgentAssignedTask` objects for successfully assigned tasks.
            - A list of `Task` objects that could not be assigned to any agent.
        """
        
        logging.info(f"Selecting agents for {len(tasks)} tasks")
        
        router_prompt = build_router_prompt()
        agent_info = [(agent.name, agent.full_description) for agent in agents]
        task_info = [(task.identifier, task.description) for task in tasks]

        response = self.client.call(
            user_query=user_query,
            system_prompt=router_prompt,
            prompt_kwargs={"agents": agent_info, "tasks": task_info},
        )
        selected_agents = response.selected_agents
        logging.info(f"LLM selected {len(selected_agents)} agent-task pairs")

        unassigned_tasks = []
        assigned_tasks = []
        for agent_id, task_id in selected_agents:
            logging.info(f"Processing agent-task pair: {agent_id} - {task_id}")
            for task in tasks:
                if task.identifier == task_id[1]:
                    matching_agent = next(
                        (agent for agent in agents if agent.name == agent_id[1]), None
                    )
                    if matching_agent:
                        logging.info(
                            f"Assigned task '{task.identifier}' to agent '{matching_agent.name}'"
                        )
                        agent_assigned_task = AgentAssignedTask(
                            identifier=task.identifier,
                            description=task.description,
                            operations=task.operations,
                            agent=matching_agent
                        )
                        assigned_tasks.append(agent_assigned_task)
                    else:
                        logging.info(
                            f"Could not find matching agent '{agent_id[1]}' for task '{task.identifier}'"
                        )
                        unassigned_tasks.append(task)

        logging.info(
            f"Assignment complete: {len(assigned_tasks)} tasks assigned, {len(unassigned_tasks)} tasks unassigned"
        )
        return assigned_tasks, unassigned_tasks
