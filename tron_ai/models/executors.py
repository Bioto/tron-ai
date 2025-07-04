from pydantic import BaseModel
from typing import Optional
from tron_ai.models.prompts import Prompt
from tron_ai.utils.LLMClient import LLMClient


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
