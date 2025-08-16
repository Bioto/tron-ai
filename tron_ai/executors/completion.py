
import pydantic
from typing import Optional

from tron_ai.executors.base import Executor
from adalflow.core.tool_manager import ToolManager


class CompletionExecutor(Executor):
    async def execute(
        self,
        user_query: str,
        tool_manager: Optional[ToolManager] = None,
        prompt_kwargs: dict = {},
    ) -> pydantic.BaseModel:
        return self.client.fcall(
            user_query=user_query,
            system_prompt=self._config.prompt,
            tool_manager=tool_manager,
            prompt_kwargs=prompt_kwargs
        )
