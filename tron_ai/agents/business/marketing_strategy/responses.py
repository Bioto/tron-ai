from pydantic import BaseModel
from pydantic import Field
from tron_ai.models.prompts import PromptMeta
from typing import List, Optional
from tron_ai.models.prompts import ToolCall


class MarketerResponse(PromptMeta, BaseModel):
    """
    Structured response model for the Marketer agent.

    Fields:
        summary (str): Brief overview of how the response addresses the request and aligns with marketing best practices.
        key_strategy_insights (List[str]): 2-3 bullet points drawing from research (e.g., Deploy-Reshape-Invent application).
        generated_output (str): The main content (e.g., social media post, email campaign, strategy outline) in markdown.
        recommendations (List[str]): Actionable next steps, including KPIs and potential A/B tests.
        questions_for_refinement (List[str]): 1-2 questions to improve future outputs.
        user_questions (List[str]): 1-2 questions to ask the user for missing information or clarification.
        tool_calls (Optional[List[ToolCall]]): List of tools called during agent execution with their keyword arguments.
    """

    response: str = Field(
        ...,
        description="A brief overview of how this response addresses the request and aligns with marketing best practices."
    )
    generated_output: str = Field(
        "",
        description="The main content (e.g., social media post, email campaign, strategy outline) in markdown format."
    )
    key_strategy_insights: List[str] = Field(
        default_factory=list,
        description="2-3 bullet points drawing from research (e.g., Deploy-Reshape-Invent application)."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable next steps, including KPIs to measure success and potential A/B tests."
    )
    questions_for_refinement: List[str] = Field(
        default_factory=list,
        description="1-2 questions to improve future outputs."
    )
    user_questions: List[str] = Field(
        default_factory=list,
        description="1-2 questions to ask the user for missing information or clarification."
    )
    tool_calls: Optional[List[ToolCall]] = Field(
        default_factory=list,
        description="List of tools called during agent execution with their keyword arguments."
    )