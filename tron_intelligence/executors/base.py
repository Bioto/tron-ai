from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional
from tron_intelligence.prompts.models import Prompt
from tron_intelligence.utils.LLMClient import LLMClient


class ExecutorConfig(BaseModel):
    # Model Settings
    model_config = {
        "arbitrary_types_allowed": True,
    }
    # Client should be the only required field
    client: LLMClient = None

    # Prompt is optional
    prompt: Optional[Prompt] = None

    logging: bool = False


class BaseExecutor(ABC):
    def __init__(self, config: ExecutorConfig, *args, **kwargs):
        self._config = config

    @property
    def client(self) -> LLMClient:
        return self._config.client

    @property
    def prompt(self) -> Prompt:
        return self._config.prompt

    @abstractmethod
    def execute(self, *args, **kwargs) -> BaseModel:
        pass
