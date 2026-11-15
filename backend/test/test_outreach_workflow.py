
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.research_agent import ResearchReport
from app.agents.reviewer_agent import EmailReview, FlaggedClaim, ReviewerOutput
from app.agents.writer_agent import EmailDraft
from app.schemas.outreach import RunSellerSnapshot
from app.services.outreach_service import build_signature
from app.workflows.outreach_workflow import (
    build_safety_rules,
    finalize_draft,
    find_placeholders,
    passes_review,
    quote_in_email,
    run_outreach,
    to_email_review,
)


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


def as_output(review: EmailReview) -> ReviewerOutput:
    """What the reviewer model returns for a review without flags."""
    assert not review.unsupported_claims
    return ReviewerOutput(
        **review.model_dump(exclude={"unsupported_claims", "ignored_claims"}),
        flagged_claims=[],
    )


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
        mock_run_result(as_output(approved_review)),
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
        mock_run_result(as_output(rejected_review)),
        mock_run_result(improved_email),
        mock_run_result(as_output(approved_review)),
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
        mock_run_result(as_output(rejected_review)),  # First review
        mock_run_result(email_draft),  # First improvement
        mock_run_result(as_output(rejected_review)),  # Second review
        mock_run_result(email_draft),  # Second improvement
        mock_run_result(as_output(rejected_review)),  # Final review
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


@pytest.mark.anyio
async def test_context_reaches_every_agent_prompt(
    research_report: ResearchReport,
    email_draft: EmailDraft,
    rejected_review: EmailReview,
    approved_review: EmailReview,
):
    """Seller, product and contact context must reach every agent after research."""

    context = {
        "selected_product": {"name": "Call Forward System (SLQ5)"},
        "selected_contact": {
            "name": "Jane Doe",
            "backend_verification_status": "NOT_VERIFIED",
        },
    }

    mock_results = [
        mock_run_result(research_report),  # Research
        mock_run_result(email_draft),  # Writer
        mock_run_result(as_output(rejected_review)),  # Review
        mock_run_result(email_draft),  # Improver
        mock_run_result(as_output(approved_review)),  # Re-review
    ]

    with patch(
        "app.workflows.outreach_workflow.Runner.run",
        new_callable=AsyncMock,
        side_effect=mock_results,
    ) as mock_run:
        await run_outreach(
            company_info="Example Ltd",
            sender_offering="Queue management solutions",
            outreach_context=context,
        )

    calls = mock_run.await_args_list
    assert len(calls) == 5

    agent_names = [call.args[0].name for call in calls]
    assert agent_names == [
        "Company Research Agent",
        "Cold Email Writer",
        "Cold Email Reviewer",
        "Cold Email Improver",
        "Cold Email Reviewer",
    ]

    # Every step after research receives the full selection context.
    for call in calls[1:]:
        prompt = call.args[1]
        assert "Call Forward System (SLQ5)" in prompt
        assert "Jane Doe" in prompt
        assert "NOT_VERIFIED" in prompt
        assert "Do not claim that a contact currently holds" in prompt


# --------------------------------------------------
# Reviewer flags must quote the email
# --------------------------------------------------

DRAFT = EmailDraft(
    subject="Call Forward System for your service points",
    body=(
        "Dear Jane Doe,\n\nTensator\u2019s Call Forward System calls the next "
        "customer to an available service point.\n\n"
        "With more than 1,000 stores, customer flow matters."
    ),
    call_to_action="Would a 20-minute call be useful?",
)


def reviewer_output(flags: list[tuple[str, str]], score: float = 9) -> ReviewerOutput:
    return ReviewerOutput(
        personalization=8,
        clarity=9,
        relevance=9,
        cta_quality=9,
        flagged_claims=[FlaggedClaim(quote=q, problem=p, supported=False) for q, p in flags],
        improvement_suggestions=[],
        overall_score=score,
        approved=False,
    )


@pytest.mark.parametrize(
    ("quote", "found"),
    [
        ("more than 1,000 stores", True),
        ("MORE THAN 1,000   STORES", True),  # case and spacing
        ("Tensator's Call Forward System", True),  # straight vs curly apostrophe
        ('"calls the next customer"', True),  # wrapped in quotes
        ("customer flow matters...", True),  # trailing ellipsis
        ("Would a 20-minute call be useful?", True),  # from the call to action
        ("Call Forward System for your service points", True),  # from the subject
        ("as Retail Director", False),  # not in the email
        ("", False),
        ("a", False),  # too short to mean anything
    ],
)
def test_quote_in_email(quote: str, found: bool):
    assert quote_in_email(quote, DRAFT) is found


def test_flags_without_matching_quote_are_ignored():
    review = to_email_review(
        reviewer_output([
            ("more than 1,000 stores", "Exact figure is 1,059"),
            ("as Retail Director", "Job title is unverified"),
        ]),
        DRAFT,
    )

    assert review.unsupported_claims == ['"more than 1,000 stores": Exact figure is 1,059']
    assert review.ignored_claims == ['"as Retail Director": Job title is unverified (quote not found in the email)']


def test_pass_rule_ignores_reviewer_approved_flag():
    """Only a wrong flag made the reviewer say no; it must not block."""
    review = to_email_review(
        reviewer_output([("as Retail Director", "Job title is unverified")]),
        DRAFT,
    )

    assert review.approved is False
    assert passes_review(review) is True


def test_pass_rule_still_needs_score_and_no_real_flags():
    low_score = to_email_review(reviewer_output([], score=7.5), DRAFT)
    real_flag = to_email_review(
        reviewer_output([("more than 1,000 stores", "Unsupported")]),
        DRAFT,
    )

    assert passes_review(low_score) is False
    assert passes_review(real_flag) is False


@pytest.mark.anyio
async def test_wrong_flag_does_not_trigger_rewrites(
    research_report: ResearchReport,
    email_draft: EmailDraft,
):
    """A flag about text that is not in the email must not cost a rewrite."""
    mock_results = [
        mock_run_result(research_report),
        mock_run_result(email_draft),
        mock_run_result(reviewer_output([("as Retail Director", "Unverified title")])),
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

    assert mock_run.await_count == 3
    assert result.approved is True
    assert result.improvement_count == 0
    assert result.review.unsupported_claims == []
    assert result.review.ignored_claims == ['"as Retail Director": Unverified title (quote not found in the email)']


def test_placeholders_always_fail_the_review():
    """Run 09 passed with "[Your Name]" in it; the code now catches that."""
    draft = DRAFT.model_copy(update={
        "body": DRAFT.body + "\n\nBest regards,\n[Your Name]\n[Your Name]\n{{company}}",
    })

    review = to_email_review(reviewer_output([], score=9), draft)

    assert review.unsupported_claims == [
        '"[Your Name]": Unfilled placeholder. Replace it before sending.',
        '"{{company}}": Unfilled placeholder. Replace it before sending.',
    ]
    assert passes_review(review) is False


def test_no_placeholders_no_flags():
    assert to_email_review(reviewer_output([], score=9), DRAFT).unsupported_claims == []


def test_flags_marked_supported_are_ignored():
    """Run 10: 'This claim matches approved product facts and thus is accurate'."""
    output = reviewer_output([])
    output.flagged_claims = [
        FlaggedClaim(
            quote="Call Forward System calls the next customer",
            problem="Matches approved product facts and is accurate",
            supported=True,
        ),
    ]

    review = to_email_review(output, DRAFT)

    assert review.unsupported_claims == []
    assert review.ignored_claims == [
        (
            '"Call Forward System calls the next customer": Matches approved '
            "product facts and is accurate (reviewer marked it as supported)"
        ),
    ]
    assert passes_review(review) is True


# --------------------------------------------------
# Signature and call to action (problems 2 and 3)
# --------------------------------------------------

SIGNATURE = "Kind regards,\nSam Seller\nSales Manager, Tensator"


def test_signature_replaces_ai_sign_off_and_placeholders():
    draft = EmailDraft(
        subject="Customer flow at your stores",
        body=(
            "Hello,\n\nOur Call Forward System guides customers to free counters.\n\n"
            "Would a short call next week be useful?\n\nBest regards,\n[Your Name]\nTensator"
        ),
        call_to_action="Would a short call next week be useful?",
    )

    final = finalize_draft(draft, SIGNATURE)

    assert final.body.endswith(SIGNATURE)
    assert "[Your Name]" not in final.body
    assert "Best regards" not in final.body
    assert final.body.count("Would a short call next week be useful?") == 1
    assert find_placeholders(final) == []


def test_missing_call_to_action_is_added_before_signature():
    draft = EmailDraft(
        subject="Customer flow at your stores",
        body="Hello,\n\nOur Call Forward System guides customers to free counters.",
        call_to_action="Would a short call next week be useful?",
    )

    body = finalize_draft(draft, SIGNATURE).body

    assert body.index("Would a short call") < body.index("Kind regards")


def test_closing_sentence_is_not_mistaken_for_a_sign_off():
    draft = EmailDraft(
        subject="Customer flow at your stores",
        body=(
            "Hello,\n\nOur Call Forward System guides customers to free counters.\n\n"
            "Thank you for taking the time to read this message today."
        ),
        call_to_action="Thank you for taking the time to read this message today.",
    )

    assert "Thank you for taking the time" in finalize_draft(draft, SIGNATURE).body


def test_without_signature_the_draft_is_unchanged():
    assert finalize_draft(DRAFT, None) == DRAFT


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({}, None),  # no sender name: no signature
        (
            {"sender_name": "Sam Seller"},
            "Best regards,\nSam Seller\nTensator",
        ),
        (
            {
                "sender_name": "Sam Seller",
                "sender_job_title": "Sales Manager",
                "sign_off": "Kind regards,",
                "sender_phone": "+44 20 0000 0000",
                "sender_email": "sam@tensator.example",
            },
            (
                "Kind regards,\nSam Seller\nSales Manager, Tensator\n"
                "+44 20 0000 0000 · sam@tensator.example"
            ),
        ),
    ],
)
def test_build_signature(fields: dict, expected: str | None):
    seller = RunSellerSnapshot(id=1, name="Tensator", **fields)
    assert build_signature(seller) == expected


@pytest.mark.parametrize(
    ("style", "text"),
    [
        ("call", "asks for a short phone call"),
        ("email", "invites them to reply to this email"),
    ],
)
def test_call_to_action_style_in_rules(style: str, text: str):
    rules = build_safety_rules({"call_to_action_style": style})
    assert text in rules
    assert "Do not write a sign-off" in rules


# --------------------------------------------------
# One email, one ask (Waitrose Run 1)
# --------------------------------------------------

WAITROSE_BODY = (
    "Hi Helen Carroll,\n\n"
    "Our Call Forward System (SLQ5) offers an adaptable queue management solution.\n\n"
    "Would you be open to discussing how this solution might integrate with your "
    "existing customer service setup?\n\n"
    "Please reply to this email if you would like to explore this further."
)
REPLY_CTA = "Please reply to this email if you would like to explore this further."


def test_question_before_the_call_to_action_is_removed():
    draft = EmailDraft(subject="Queue management", body=WAITROSE_BODY, call_to_action=REPLY_CTA)

    body = finalize_draft(draft, SIGNATURE).body

    assert "Would you be open to discussing" not in body
    assert body.count("?") == 0
    assert body.index(REPLY_CTA) < body.index("Kind regards")


def test_question_that_is_the_call_to_action_is_kept():
    cta = "Would a short call next week be useful?"
    draft = EmailDraft(
        subject="Queue management",
        body="Hello,\n\nOur Call Forward System guides customers to free counters.\n\n" + cta,
        call_to_action=cta,
    )

    assert cta in finalize_draft(draft, SIGNATURE).body


def test_earlier_question_is_kept():
    """Only a question directly before the call to action counts as a second ask."""
    draft = EmailDraft(
        subject="Queue management",
        body=(
            "Hello,\n\nAre busy periods a challenge at your service desks?\n\n"
            "Our Call Forward System guides customers to free counters.\n\n" + REPLY_CTA
        ),
        call_to_action=REPLY_CTA,
    )

    assert "Are busy periods a challenge" in finalize_draft(draft, SIGNATURE).body


def test_greeting_and_single_question_rules():
    rules = build_safety_rules({"selected_contact": {"name": "Helen Carroll"}})

    assert "first name only" in rules
    assert "Ask only one question" in rules
