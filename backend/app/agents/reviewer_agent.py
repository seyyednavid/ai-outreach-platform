
from agents import Agent
from pydantic import BaseModel, Field


class EmailReview(BaseModel):
    personalization: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    cta_quality: int = Field(ge=0, le=10)

    unsupported_claims: list[str]
    improvement_suggestions: list[str]

    overall_score: float = Field(ge=0, le=10)
    approved: bool


reviewer_agent = Agent(
    name="Cold Email Reviewer",
    model="gpt-4.1-mini",
    instructions="""
    You are a strict B2B outreach email reviewer.

    Evaluate the email against the supplied research
    and the sender's actual offering.

    Score each category from 0 to 10:
    - Personalization
    - Clarity
    - Relevance
    - CTA quality

    Identify:
    - Unsupported company claims
    - Generic or exaggerated statements
    - Weak personalization
    - Unclear or duplicated calls to action

    Approval rules:
    - Overall score must be at least 8.
    - No unsupported factual claims.
    - The offering must be accurately represented.
    - The email must contain a clear CTA.

    Be critical and give actionable suggestions.
    Return structured output.
    """,
    output_type=EmailReview,
)
