from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta

class AIEthicsResponse(PromptMeta, BaseModel):
    """
    Structured response model for the AI Ethics agent.
    """
    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with AI ethics best practices."
    ) 