from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta

class SalesResponse(PromptMeta, BaseModel):
    """
    Structured response model for the Sales agent.
    """
    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with consultative sales best practices."
    ) 