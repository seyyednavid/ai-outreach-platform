
import json

from agents import Runner
from pydantic import BaseModel

from app.agents.improver_agent import improver_agent
from app.agents.research_agent import ResearchReport, research_agent
from app.agents.reviewer_agent import EmailReview, reviewer_agent
from app.agents.writer_agent import EmailDraft, writer_agent

MAX_IMPROVEMENTS = 2
MIN_APPROVAL_SCORE = 8.0


class OutreachResult(BaseModel):
    research: ResearchReport
    email: EmailDraft
    review: EmailReview
    approved: bool
    improved: bool
    improvement_count: int
    requires_human_review: bool = True


def build_prompt(task: str, **context: object) -> str:
    return (
        f"{task}\n\n"
        + json.dumps(context, indent=2, ensure_ascii=False)
    )


def passes_review(review: EmailReview) -> bool:
    return (
        review.overall_score >= MIN_APPROVAL_SCORE
        and not review.unsupported_claims
        and review.approved
    )


async def run_outreach(
    company_info: str,
    sender_offering: str,
) -> OutreachResult:
    # 1. Research
    research_result = await Runner.run(
        research_agent,
        company_info,
    )
    research = research_result.final_output

    # 2. Write
    write_result = await Runner.run(
        writer_agent,
        build_prompt(
            "Write a personalized outreach email.",
            research=research.model_dump(mode="json"),
            sender_offering=sender_offering,
        ),
    )
    email = write_result.final_output

    # 3. Review
    async def review_email(draft: EmailDraft) -> EmailReview:
        result = await Runner.run(
            reviewer_agent,
            build_prompt(
                "Review this email against the evidence.",
                email=draft.model_dump(mode="json"),
                research=research.model_dump(mode="json"),
                sender_offering=sender_offering,
            ),
        )
        return result.final_output

    review = await review_email(email)
    improvement_count = 0

    # 4. Bounded feedback loop
    while (
        not passes_review(review)
        and improvement_count < MAX_IMPROVEMENTS
    ):
        improve_result = await Runner.run(
            improver_agent,
            build_prompt(
                "Improve the email using the review feedback.",
                original_email=email.model_dump(mode="json"),
                review=review.model_dump(mode="json"),
                research=research.model_dump(mode="json"),
                sender_offering=sender_offering,
            ),
        )

        email = improve_result.final_output
        improvement_count += 1

        # Review every improved version
        review = await review_email(email)

    # 5. Final decision
    return OutreachResult(
        research=research,
        email=email,
        review=review,
        approved=passes_review(review),
        improved=improvement_count > 0,
        improvement_count=improvement_count,
        requires_human_review=True,
    )
