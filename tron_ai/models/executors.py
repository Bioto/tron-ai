from pydantic import BaseModel
from typing import Optional, Any, TYPE_CHECKING
from tron_ai.models.prompts import Prompt

if TYPE_CHECKING:
    from tron_ai.utils.llm.LLMClient import LLMClient

class ExecutorConfig(BaseModel):
    # Model Settings
    model_config = {
        "arbitrary_types_allowed": True,
    }
    # Client should be the only required field - use Any to avoid forward reference issues
    client: Optional[Any] = None

    # Prompt is optional
    prompt: Optional[Prompt] = None

    logging: bool = False
