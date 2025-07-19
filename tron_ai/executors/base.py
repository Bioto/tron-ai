from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import logging

from pydantic import BaseModel
from tron_ai.models.prompts import Prompt
from tron_ai.models.executors import ExecutorConfig

if TYPE_CHECKING:
    from tron_ai.utils.llm.LLMClient import LLMClient


class Executor(ABC):
    _config: ExecutorConfig = None
    logger: logging.Logger = None
    
    def __init__(self, config: ExecutorConfig, *args, **kwargs):
        self._config = config
        
        if self._config.logging:
            self.logger = logging.getLogger(__name__)   

    @property
    def client(self) -> 'LLMClient':
        return self._config.client

    @property
    def prompt(self) -> Prompt:
        return self._config.prompt

    @abstractmethod
    def execute(self, *args, **kwargs) -> BaseModel:
        pass
