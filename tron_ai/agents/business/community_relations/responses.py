from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta

class CommunityRelationsResponse(PromptMeta, BaseModel):
    """
    Structured response model for the Community Relations agent.
    """
    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with community relations best practices."
    ) 