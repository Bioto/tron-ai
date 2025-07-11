import os
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tron_ai.models.prompts import Prompt, BasePromptResponse
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from adalflow.core.tool_manager import ToolManager

class MissingEnvironmentVariable(Exception):
    pass


class Agent(BaseModel):
    """Represents a configurable, tool-augmented agent.

    This class defines the core structure of an agent within the system. Each agent
    has a distinct identity, a set of capabilities described by its prompt and
    associated tools, and can be converted into a standardized format for
    interoperability.

    Attributes:
        name: The unique name of the agent.
        description: A brief description of the agent's purpose and capabilities.
        supports_multiple_operations: Flag indicating if the agent can handle
            multiple tasks or operations in a single request.
        prompt: The base prompt that defines the agent's behavior and personality.
        tool_manager: An optional manager for any tools or skills the agent can use.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str
    description: str
    
    supports_multiple_operations: bool = True
    
    prompt: Prompt

    tool_manager: Optional[ToolManager] = None
    
    required_env_vars: List[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_environment_variables(self) -> 'Agent':
        for env_var in self.required_env_vars:
            if env_var not in os.environ:
                raise MissingEnvironmentVariable(f"Environment variable {env_var} is required")
        return self

    @property
    def full_description(self):
        """Provides a detailed description of the agent, including its tools.

        Returns:
            A string combining the agent's base description with a list of the
            names of the tools it has available.
        """
        desc = f"{self.name}: {self.description}"
        if self.tool_manager:
            tool_names = [tool.definition.func_name for tool in self.tool_manager.tools]
            desc += f"\n\nTools: {', '.join(tool_names)}"
        return desc

    def to_a2a_card(self) -> AgentCard:
        """Converts the agent's definition into a standard A2A AgentCard.

        This method facilitates interoperability by representing the agent's
        metadata, capabilities, and skills in the Agent-to-Agent (A2A)
        communication protocol format.

        Returns:
            An AgentCard instance populated with the agent's details.
        """
        capabilities = AgentCapabilities()
        skills = [  
            AgentSkill(
                id=self.name,
                name=self.name,
                description=self.description,
                tags=["skill"],
            )
        ]
        if self.tool_manager:
            for tool in self.tool_manager.tools:
                skills.append(
                    AgentSkill(
                        id=tool.definition.func_name,
                        name=tool.definition.func_name,
                        description=getattr(tool.definition, 'description', ''),
                        tags=["tool"],
                    )
                )
        return AgentCard(
            name=self.name,
            description=self.description,
            capabilities=capabilities,
            skills=skills,
            url="http://127.0.0.1:8000/",
            version="1.0.0",
            defaultInputModes=["text", "text/plain"],
            defaultOutputModes=["text", "text/plain"],
        )

    
class AgentExecutorResponse(BasePromptResponse):
    """Represents the output from a single agent's execution.

    This model encapsulates all relevant information returned by an agent after
    it has processed a request.

    Attributes:
        agent_name: The name of the agent that produced this response.
        response: The primary textual response or output from the agent.
    """
    agent_name: Optional[str] = Field(
        default=None,
        description="Name of the agent that generated the response"
    )
    response: str = Field(
        default="",
        description="Response from the agent"
    )
    
class AgentExecutorResults(BaseModel):
    """A container for collecting results from multiple agent executions.

    This model is used to aggregate a list of `AgentExecutorResponse` objects,
    which is particularly useful in scenarios involving parallel or sequential
    execution of multiple agents.

    Attributes:
        results: A list of `AgentExecutorResponse` objects, each containing
            the output from a single agent execution.
    """
    results: List[AgentExecutorResponse] = Field(
        default_factory=list,
        description="List of responses from multiple agents when executing in parallel"
    )