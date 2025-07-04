from adalflow import Prompt
import pydantic
from typing import Optional

from tron_ai.executors.base import BaseExecutor
from adalflow.core.tool_manager import ToolManager


class CompletionExecutor(BaseExecutor):
    async def execute(
        self,
        user_query: str,
        system_prompt: Prompt,
        tool_manager: Optional[ToolManager] = None,
        prompt_kwargs: dict = {},
    ) -> pydantic.BaseModel:
        return self.client.fcall(
            user_query=user_query,
            system_prompt=system_prompt,
            tool_manager=tool_manager,
            prompt_kwargs=prompt_kwargs
        )
