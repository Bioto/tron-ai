from abc import ABC, abstractmethod
from typing import Any


class BaseProcessor(ABC):
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        raise NotImplementedError
    