from typing import Optional, List
from pydantic import BaseModel, Field
from tron_intelligence.prompts.models import Prompt, PromptMeta


ROUTER_PROMPT = """
You are a router for a set of agents. You are given a set of agents and a set of tasks. You need to select the most appropriate agent for each task.

Available Agents:
{% for agent in agents %}
- Name: {{agent[0]}}
  Description: {{agent[1]}}
{% endfor %}

Available Tasks:
{% for task in tasks %}
- ID: {{task[0]}}
  Description: {{task[1]}}
{% endfor %}

Your response should include:
- selected_agents: A list of AgentRouterSelectedAgent objects, where each object contains:
  - agent_name: The name of the selected agent (string)
  - task_id: The ID of the task assigned to that agent (string)
  Set to empty list if no agents are selected.
- confidence: A float between 0 and 1 indicating your confidence in the selected agent assignments. Higher values indicate greater confidence that the agents can effectively complete their assigned tasks. Set to null if no agent is selected.
"""


class AgentRouterSelectedAgent(BaseModel):
    """Represents a selected agent and task pairing from the router.

    This model captures the mapping between an agent and the specific task they were selected to handle.
    It is used to track which agents were assigned to which tasks during the routing process.

    Attributes:
        agent_name (str): The name identifier of the selected agent
        task_id (str): The unique identifier of the task this agent was selected for
    """

    agent_name: str = Field(description="The name identifier of the selected agent")
    task_id: str = Field(
        description="The unique identifier of the task this agent was selected for"
    )


class AgentRouterResults(PromptMeta, BaseModel):
    """Results from the agent router containing the selected agent-task pairings and confidence score.

    This model represents the output from the agent router which determines the most appropriate
    agent to handle each task based on agent capabilities and task requirements. The router
    analyzes the available agents and tasks to create optimal one-to-one pairings that maximize
    the likelihood of successful task completion.

    Attributes:
        selected_agents (List[AgentRouterSelectedAgent]): A list of agent-task pairings, where each
            pairing is represented by a single AgentRouterSelectedAgent object containing one agent name
            and one task ID. The list will be empty if no suitable agent-task matches were found.
            Each agent can only be paired with one task, and each task can only be assigned to one agent.

        confidence (Optional[float]): A confidence score between 0 and 1 indicating the router's
            assessment of how well the selected one-to-one agent-task pairings match. Higher scores
            (closer to 1) indicate stronger matches where agents are highly qualified for their assigned
            tasks. Lower scores (closer to 0) suggest less optimal matches. Will be None if no agents
            were selected. This score considers factors like agent capabilities, task requirements,
            and the overall fit of the assignments.
    """

    selected_agents: List[AgentRouterSelectedAgent] = Field(
        description="List of agent-task pairings, each containing an agent name and their assigned task ID",
        default=[],
    )
    confidence: Optional[float] = Field(
        description="Confidence score (0-1) indicating the quality of the agent-task matches",
        default=None,
    )


def build_router_prompt(prompt: str = ROUTER_PROMPT) -> Prompt:
    return Prompt(
        text=prompt,
        output_format=AgentRouterResults,
    )
