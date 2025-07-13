from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta

class ProductManagementResponse(PromptMeta, BaseModel):
    """
    Structured response model for the Product Management agent.
    """
    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with product management best practices."
    ) 