from abc import ABC, abstractmethod
from typing import Any

class BaseFlow(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        raise NotImplementedError