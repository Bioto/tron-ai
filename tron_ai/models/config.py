"""Configuration models for the tron_ai framework."""

from pydantic import BaseModel
from typing import Optional

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
    logging: bool = False
    json_output: bool = True
    
    max_tokens: Optional[int] = None
    
    def build_model_kwargs(self):
        return {
            "model": self.model_name,
        }
        
    @staticmethod
    def build(**kwargs) -> 'LLMClientConfig':
        return LLMClientConfig(**kwargs)


class BaseChatGPT5Config(LLMClientConfig):
    model_name: str = "gpt-5"
    
    max_tokens: Optional[int] = 128000
    
    reasoning_effort: str = "low"
    text_verbosity: str = "low"
    
    def build_model_kwargs(self):
        return super().build_model_kwargs() | {
            "max_completion_tokens": self.max_tokens,
            "reasoning_effort": self.reasoning_effort,
        }
        
    @staticmethod
    def build_config(**kwargs):
        return BaseChatGPT5Config(**kwargs)
        

class ChatGPT5LowConfig(BaseChatGPT5Config):
    reasoning_effort: str = "low"
    
class ChatGPT5MediumConfig(BaseChatGPT5Config):
    reasoning_effort: str = "medium"
    
class ChatGPT5HighConfig(BaseChatGPT5Config):
    reasoning_effort: str = "high"