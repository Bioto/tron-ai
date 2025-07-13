from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta

class FinancialPlanningResponse(PromptMeta, BaseModel):
    """
    Structured response model for the Financial Planning agent.
    """
    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with financial planning best practices."
    ) 