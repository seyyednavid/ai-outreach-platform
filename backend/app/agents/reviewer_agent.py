
from agents import Agent
from pydantic import BaseModel, Field


class FlaggedClaim(BaseModel):
    quote: str = Field(
        description="The exact words from the email, copied verbatim",
    )
    problem: str = Field(
        description="Why this text is unsupported or wrong",
    )
    supported: bool = Field(
        description=(
            "True if, after checking, the evidence does support this "
            "text. Supported items do not block the email."
        ),
    )


class ReviewerOutput(BaseModel):
    """What the reviewer model returns. Converted to EmailReview in code."""

    personalization: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    cta_quality: int = Field(ge=0, le=10)

    flagged_claims: list[FlaggedClaim]
    improvement_suggestions: list[str]

    overall_score: float = Field(ge=0, le=10)
    approved: bool


class EmailReview(BaseModel):
    personalization: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    cta_quality: int = Field(ge=0, le=10)

    # Flags whose quoted text was found in the email.
    unsupported_claims: list[str]
    improvement_suggestions: list[str]

    overall_score: float = Field(ge=0, le=10)
    approved: bool

    # Flags dropped because their quote is not in the email.
    # Empty for reviews stored before 15 Nov 2026.
    ignored_claims: list[str] = Field(default_factory=list)


reviewer_agent = Agent(
    name="Cold Email Reviewer",
    model="gpt-4.1-mini",
    instructions="""
    You are a strict B2B outreach email reviewer.

    Evaluate the email against the supplied research
    and the sender's actual offering.

    Score each category from 0 to 10 for writing quality:
    - Personalization
    - Clarity
    - Relevance
    - CTA quality
    Do not lower scores because of unsupported claims;
    list those in flagged_claims instead.

    Flag claims:
    - Only flag text that is actually written in the email
      (subject, body or call to action).
    - For each flag, copy the exact words from the email into
      "quote", verbatim, and explain the problem.
    - The supplied context (contact details, product data,
      research) is background, not part of the email. Never
      flag something the email does not say.
    - A rounded number that stays true is supported, for
      example "more than 1,000 stores" when research says 1,059.
    - Product claims are supported when they match
      "approved_product_facts" (the seller's own catalogue:
      description, features, use cases). Company claims about
      the target need the research. The catalogue does not
      prove that the target company has a need.
    - Conditional or hedged sentences ("if ...", "may",
      "could", "might"), questions and offers are not factual
      claims. Flag them only if they state something false.
    - Only flag claims you judge unsupported or wrong. If you
      check a claim and the evidence supports it, either leave
      it out or set "supported" to true.

    Also identify:
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
    output_type=ReviewerOutput,
)
