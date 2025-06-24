"""Configuration models for the tron-ai framework."""

from pydantic import BaseModel


class LLMClientConfig(BaseModel):
    """Configuration for LLM clients.

    This class defines the standard configuration options for LLM clients
    used throughout the framework.

    Attributes:
        model_name: The name of the model to use
        json_output: Whether to request JSON output from the model
        logging: Whether to enable logging
    """

    model_name: str = "gpt-4o"
    json_output: bool = False
    logging: bool = False
