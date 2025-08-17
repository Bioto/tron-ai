from typing import List, Optional, Type, Dict, Any
from abc import ABC, abstractmethod
import pydantic
from pydantic import BaseModel, Field

from jinja2 import Template



class PromptDiagnostics(BaseModel):
    """Diagnostic information about a prompt's execution.

    Attributes:
        thoughts (List[str]): A list of thoughts that the model has about the inputs.
        confidence (float): A value between 0 and 1 indicating how confident the model is in its thoughts.
    """

    thoughts: List[str] = Field(
        default_factory=list,
        description="A list of thoughts that the model has about the inputs.",
    )
    confidence: float = Field(
        default=0.0,
        description="This field is used to determine if the model is confident in its thoughts. 0 - 1 as a float value.",
        ge=0.0,
        le=1.0,
    )
    
    @staticmethod
    def example() -> dict:
        return {
            "thoughts": [
                "Thought 1",
                "Thought 2",
                "Thought 3"
            ],
            "confidence": 0.8
        }


class PromptMeta(BaseModel):
    """Base metadata class for prompt responses.

    Attributes:
        diagnostics (PromptDiagnostics): Diagnostic information about the prompt execution.
    """

    diagnostics: PromptDiagnostics = Field(
        default_factory=PromptDiagnostics, description="Diagnostics for the prompt."
    )
    
    @staticmethod
    def example() -> dict:
        return {
            "diagnostics": PromptDiagnostics.example()
        }
    


class ToolCall(BaseModel):
    name: str = Field(description="The name of the tool called.")
    kwargs: Optional[Dict[str, Any]] = Field(default={}, description="The keyword arguments passed to the tool.")
    
    @staticmethod
    def example() -> dict:
        return {
            "name": "tool_name",
            "kwargs": {
                "arg1": "value1",
                "arg2": "value2"
            }
        }
    


class BasePromptResponse(PromptMeta, BaseModel, ABC):
    tool_calls: Optional[List[ToolCall]] = Field(
        default_factory=list, description="List of tools called during agent execution with their keyword arguments"
    )
    
    def generated_example(self) -> dict:
        return {
            "diagnostics": PromptDiagnostics.example(),
            "tool_calls": [
                ToolCall.example()
            ],
        } | self.example()
        
    @abstractmethod
    def example(self) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

class PromptDefaultResponse(BasePromptResponse):
    """Default response format for prompts.

    This class provides a standardized response structure for AI agent interactions,
    including both text responses and tool execution calls. It inherits from PromptMeta
    to include diagnostic information about the prompt execution.

    Attributes:
        response (Optional[str]): The text response to the prompt. Defaults to empty string.
        tool_calls (Optional[List[ToolCall]]): List of tools called during agent execution 
            with their keyword arguments. Defaults to empty list.
        diagnostics (PromptDiagnostics): Inherited diagnostic information about the prompt execution.
    """

    response: Optional[str] = Field(default="", description="Response to the prompt.")
    
    @staticmethod
    def example() -> dict:
        return {
            "response": "Response to the prompt."
        }

class Prompt(BaseModel):
    """A prompt template that can be rendered with variables.

    Attributes:
        text (str): The prompt template text.
        output_format (Type[pydantic.BaseModel]): The expected format of the response, defaults to PromptDefaultResponse.
        required_kwargs (List[str]): Required keyword arguments that must be provided when building the prompt.
    """

    text: str = Field(description="The prompt template text")
    output_format: Any = Field(
        default_factory=lambda: PromptDefaultResponse,
        description="The expected format of the response"
    )
    required_kwargs: List[str] = Field(
        default_factory=list,
        description="Required keyword arguments that must be provided when building the prompt"
    )

    def _validate_kwargs(self, kwargs: dict) -> None:
        """Validates that all required kwargs are present.

        Args:
            kwargs (dict): The keyword arguments to validate.

        Raises:
            ValueError: If a required kwarg is missing.
        """
        for kwarg in self.required_kwargs:
            if kwarg not in kwargs:
                raise ValueError(
                    f"Required keyword argument {kwarg} not found in kwargs"
                )

    def _generate_output_format(self, kwargs: dict) -> BaseModel:
        """Generates an instance of the output format with the given kwargs.

        Args:
            kwargs (dict): The keyword arguments to use.

        Returns:
            BaseModel: An instance of the output format.
        """
        return self.output_format(**kwargs)

    def build(self, **kwargs: dict) -> str:
        """Builds the prompt by rendering the template with the given kwargs.

        Args:
            **kwargs: Keyword arguments to render in the template.

        Returns:
            str: The rendered prompt.
        """
        self._validate_kwargs(kwargs)
    
        return (
            Template(self.text.strip()).render(**kwargs | {"_is_json": True}).rstrip()
        )


__all__ = ["Prompt", "PromptDiagnostics"]
