
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.research_agent import ResearchReport
from app.agents.reviewer_agent import EmailReview
from app.agents.writer_agent import EmailDraft
from app.workflows.outreach_workflow import run_outreach


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def research_report() -> ResearchReport:
    return ResearchReport(
        company_name="Example Ltd",
        industry="Retail",
        verified_findings=[],
        potential_pain_points=["Managing customer queues"],
        suggested_solution="Improve customer flow",
        personalization_angle="Retail customer experience",
    )


@pytest.fixture
def email_draft() -> EmailDraft:
    return EmailDraft(
        subject="Improving Customer Flow",
        body=(
            "Hello, we provide queue management solutions "
            "for retail environments. Our solutions may help "
            "improve the customer experience during busy periods. "
            "Would you be open to a brief conversation?"
        ),
        call_to_action="Would you be open to a brief conversation?",
    )


@pytest.fixture
def approved_review() -> EmailReview:
    return EmailReview(
        personalization=9,
        clarity=9,
        relevance=9,
        cta_quality=9,
        unsupported_claims=[],
        improvement_suggestions=[],
        overall_score=9,
        approved=True,
    )


@pytest.fixture
def rejected_review() -> EmailReview:
    return EmailReview(
        personalization=5,
        clarity=6,
        relevance=6,
        cta_quality=5,
        unsupported_claims=[],
        improvement_suggestions=["Improve personalization and CTA"],
        overall_score=5.5,
        approved=False,
    )


def mock_run_result(output):
    """Create a fake Runner result with a final_output attribute."""
    return type("MockRunResult", (), {"final_output": output})()


@pytest.mark.anyio
async def test_workflow_approved_without_improvement(
    research_report: ResearchReport,
    email_draft: EmailDraft,
    approved_review: EmailReview,
):
    """An approved first draft should skip the Improver Agent."""

    mock_results = [
        mock_run_result(research_report),
        mock_run_result(email_draft),
        mock_run_result(approved_review),
    ]

    with patch(
        "app.workflows.outreach_workflow.Runner.run",
        new_callable=AsyncMock,
        side_effect=mock_results,
    ) as mock_run:
        result = await run_outreach(
            company_info="Example Ltd",
            sender_offering="Queue management solutions",
        )

    assert result.approved is True
    assert result.improved is False
    assert result.improvement_count == 0
    assert result.requires_human_review is True
    assert result.email == email_draft
    assert mock_run.await_count == 3


@pytest.mark.anyio
async def test_workflow_approved_after_one_improvement(
    research_report: ResearchReport,
    email_draft: EmailDraft,
    rejected_review: EmailReview,
    approved_review: EmailReview,
):
    """A rejected draft should be improved and reviewed again."""

    improved_email = EmailDraft(
        subject="Reducing Waiting Times in Retail Stores",
        body=(
            "Hello, managing customer queues during peak hours "
            "can be challenging for retail businesses. "
            "We provide queue management solutions designed "
            "to improve customer flow. Would you be open "
            "to a short conversation next week?"
        ),
        call_to_action="Would you be open to a short call next week?",
    )

    mock_results = [
        mock_run_result(research_report),
        mock_run_result(email_draft),
        mock_run_result(rejected_review),
        mock_run_result(improved_email),
        mock_run_result(approved_review),
    ]

    with patch(
        "app.workflows.outreach_workflow.Runner.run",
        new_callable=AsyncMock,
        side_effect=mock_results,
    ) as mock_run:
        result = await run_outreach(
            company_info="Example Ltd",
            sender_offering="Queue management solutions",
        )

    assert result.approved is True
    assert result.improved is True
    assert result.improvement_count == 1
    assert result.requires_human_review is True
    assert result.email == improved_email
    assert result.review == approved_review
    assert mock_run.await_count == 5


@pytest.mark.anyio
async def test_workflow_stops_after_max_improvements(
    research_report: ResearchReport,
    email_draft: EmailDraft,
    rejected_review: EmailReview,
):
    """The workflow must stop after two failed improvements."""

    mock_results = [
        mock_run_result(research_report),  # Research
        mock_run_result(email_draft),  # Writer
        mock_run_result(rejected_review),  # First review
        mock_run_result(email_draft),  # First improvement
        mock_run_result(rejected_review),  # Second review
        mock_run_result(email_draft),  # Second improvement
        mock_run_result(rejected_review),  # Final review
    ]

    with patch(
        "app.workflows.outreach_workflow.Runner.run",
        new_callable=AsyncMock,
        side_effect=mock_results,
    ) as mock_run:
        result = await run_outreach(
            company_info="Example Ltd",
            sender_offering="Queue management solutions",
        )

    assert result.approved is False
    assert result.improved is True
    assert result.improvement_count == 2
    assert result.requires_human_review is True
    assert result.review == rejected_review
    assert mock_run.await_count == 7
