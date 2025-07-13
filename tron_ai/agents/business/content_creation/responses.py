from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta

class ContentCreationResponse(PromptMeta, BaseModel):
    """
    Structured response model for the Content Creation agent.
    """
    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with content creation best practices."
    ) 