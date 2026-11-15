"""
Integration tests for the outreach API.

Model calls and Gmail are mocked: these tests check request validation,
database-backed context building, persistence and the approval gates.
"""

from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.agents.research_agent import ResearchReport
from app.agents.reviewer_agent import EmailReview, FlaggedClaim, ReviewerOutput
from app.agents.writer_agent import EmailDraft
from app.models.company import Company
from app.models.company_product import CompanyProduct
from app.models.lead import Lead
from app.models.outreach_run import OutreachRun
from app.workflows.outreach_workflow import OutreachResult

RUN_WORKFLOW = "app.api.routes.outreach.run_outreach"
CREATE_GMAIL_DRAFT = "app.services.gmail_service.create_gmail_draft"

OFFERING = "Queue management solutions for retail stores."


@dataclass
class Seed:
    lead_id: int
    seller_id: int
    product_id: int
    other_seller_id: int
    other_product_id: int


def make_result(*, approved: bool) -> OutreachResult:
    return OutreachResult(
        research=ResearchReport(
            company_name="Example Retail",
            industry="Retail",
            verified_findings=[],
            potential_pain_points=["Queues at peak times"],
            suggested_solution="Customer flow",
            personalization_angle="Store experience",
        ),
        email=EmailDraft(
            subject="Customer flow at Example Retail",
            body=(
                "Hello, Tensator provides the Call Forward System "
                "for service counters. Would a short call be useful?"
            ),
            call_to_action="Would a short call next week be useful?",
        ),
        review=EmailReview(
            personalization=9 if approved else 5,
            clarity=9 if approved else 6,
            relevance=9 if approved else 6,
            cta_quality=9 if approved else 5,
            unsupported_claims=[] if approved else ["Unverified job title"],
            improvement_suggestions=[],
            overall_score=9 if approved else 5.5,
            approved=approved,
        ),
        approved=approved,
        improved=False,
        improvement_count=0,
    )


@pytest.fixture
def seed(
    session_factory: sessionmaker[Session],
) -> Generator[Seed, None, None]:
    with session_factory() as session:
        lead = Lead(
            company_name="Example Retail",
            website="https://example.com",
            industry="Retail",
            target_role="Head of Store Operations",
            pain_point="Possible queues at peak times",
        )
        seller = Company(
            name="Tensator",
            website=None,
            industry="Queue management",
            description="Queue management solutions.",
            target_customers="Retailers",
            differentiators="Hardware and software",
            sender_name="Sam Seller",
            sender_job_title="Sales Manager",
            sign_off="Kind regards",
            sender_email="sam@tensator.example",
            sender_phone="+44 20 0000 0000",
            cta_type="call",
        )
        other_seller = Company(
            name="Other Seller",
            website=None,
            industry="Other",
            description="Other.",
            target_customers="Other",
            differentiators="Other",
        )
        session.add_all([lead, seller, other_seller])
        session.flush()

        product = CompanyProduct(
            company_id=seller.id,
            name="Call Forward System (SLQ5)",
            description="Calls the next customer to a free service point.",
            features=["Service point calling"],
            use_cases=["Retail service counters"],
        )
        other_product = CompanyProduct(
            company_id=other_seller.id,
            name="Unrelated Product",
            description="Not sold by Tensator.",
            features=[],
            use_cases=[],
        )
        session.add_all([product, other_product])
        session.commit()

        data = Seed(
            lead_id=lead.id,
            seller_id=seller.id,
            product_id=product.id,
            other_seller_id=other_seller.id,
            other_product_id=other_product.id,
        )

    yield data

    with session_factory() as session:
        session.query(OutreachRun).delete()
        session.query(CompanyProduct).delete()
        session.query(Company).delete()
        session.query(Lead).delete()
        session.commit()


def contact_payload(status: str = "NEEDS_REVIEW") -> dict:
    return {
        "name": "Jane Doe",
        "job_title": "Head of Store Operations",
        "source_url": "https://www.theorg.com/example/jane-doe",
        "evidence_status": status,
    }


def run_payload(seed: Seed, **overrides) -> dict:
    payload = {
        "lead_id": seed.lead_id,
        "sender_offering": OFFERING,
        "seller_company_id": seed.seller_id,
        "selected_product_id": seed.product_id,
        "selected_contact": contact_payload(),
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not None}


def create_run(
    db_client: TestClient,
    seed: Seed,
    *,
    approved: bool,
) -> dict:
    with patch(
        RUN_WORKFLOW,
        new_callable=AsyncMock,
        return_value=make_result(approved=approved),
    ):
        response = db_client.post(
            "/api/v1/outreach/run",
            json=run_payload(seed),
        )
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------
# Context propagation
# --------------------------------------------------


def test_selected_context_reaches_workflow_from_database(
    db_client: TestClient,
    seed: Seed,
):
    with patch(
        RUN_WORKFLOW,
        new_callable=AsyncMock,
        return_value=make_result(approved=True),
    ) as workflow:
        response = db_client.post(
            "/api/v1/outreach/run",
            json=run_payload(seed),
        )

    assert response.status_code == 200, response.text
    workflow.assert_awaited_once()

    kwargs = workflow.await_args.kwargs
    context = kwargs["outreach_context"]

    assert kwargs["sender_offering"] == OFFERING
    assert "Example Retail" in kwargs["company_info"]

    # Seller and product facts come from PostgreSQL.
    assert context["seller_company"]["name"] == "Tensator"
    # Signature details never reach the AI; the code adds them.
    assert "sender_phone" not in context["seller_company"]
    assert "sender_email" not in context["seller_company"]
    assert context["call_to_action_style"] == "call"
    assert kwargs["signature"] == (
        "Kind regards,\nSam Seller\nSales Manager, Tensator\n"
        "+44 20 0000 0000 · sam@tensator.example"
    )
    assert context["selected_product"] == {
        "id": seed.product_id,
        "name": "Call Forward System (SLQ5)",
        "description": "Calls the next customer to a free service point.",
        "features": ["Service point calling"],
        "use_cases": ["Retail service counters"],
    }
    assert "product_selection_notice" in context

    # Only the contact's name reaches the agents, never the reported
    # job title, and the browser's evidence status is not trusted.
    contact = context["selected_contact"]
    assert contact == {
        "name": "Jane Doe",
        "backend_verification_status": "NOT_VERIFIED",
    }
    assert "Do not mention or imply their job title" in (
        context["contact_safety_notice"]
    )


def test_run_persists_context_snapshot(
    db_client: TestClient,
    seed: Seed,
):
    run = create_run(db_client, seed, approved=True)

    assert run["context"] == {
        "sender_offering": OFFERING,
        "seller_company": {
            "id": seed.seller_id,
            "name": "Tensator",
            "industry": "Queue management",
            "description": "Queue management solutions.",
            "target_customers": "Retailers",
            "differentiators": "Hardware and software",
            "sender_name": "Sam Seller",
            "sender_job_title": "Sales Manager",
            "sign_off": "Kind regards",
            "sender_email": "sam@tensator.example",
            "sender_phone": "+44 20 0000 0000",
            "cta_type": "call",
        },
        "selected_product": {
            "id": seed.product_id,
            "name": "Call Forward System (SLQ5)",
            "description": "Calls the next customer to a free service point.",
            "features": ["Service point calling"],
            "use_cases": ["Retail service counters"],
        },
        "selected_contact": {
            "name": "Jane Doe",
            "reported_job_title": "Head of Store Operations",
            "source_url": "https://www.theorg.com/example/jane-doe",
            "client_evidence_status": "NEEDS_REVIEW",
            "backend_verification_status": "NOT_VERIFIED",
        },
    }

    history = db_client.get(f"/api/v1/outreach/leads/{seed.lead_id}/runs")
    assert history.status_code == 200
    assert history.json()[0]["context"] == run["context"]


def test_run_without_selection_has_minimal_context(
    db_client: TestClient,
    seed: Seed,
):
    with patch(
        RUN_WORKFLOW,
        new_callable=AsyncMock,
        return_value=make_result(approved=True),
    ) as workflow:
        response = db_client.post(
            "/api/v1/outreach/run",
            json={"lead_id": seed.lead_id, "sender_offering": OFFERING},
        )

    assert response.status_code == 200, response.text
    context = workflow.await_args.kwargs["outreach_context"]
    assert "seller_company" not in context
    assert "selected_product" not in context
    assert "selected_contact" not in context
    assert response.json()["context"]["selected_product"] is None
    # Without a company there is no signature, so the draft cannot pass.
    assert workflow.await_args.kwargs["signature"] is None
    claims = response.json()["review"]["unsupported_claims"]
    assert any("No sender name" in claim for claim in claims)
    assert response.json()["approved"] is False
    assert response.json()["review_passed"] is False


# --------------------------------------------------
# Request validation and product ownership
# --------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "status_code", "detail"),
    [
        ({"lead_id": 999_999}, 404, "Lead not found"),
        ({"seller_company_id": 999_999}, 404, "Seller company not found"),
        ({"selected_product_id": 999_999}, 404, "Selected product not found"),
    ],
)
def test_missing_records_are_rejected(
    db_client: TestClient,
    seed: Seed,
    overrides: dict,
    status_code: int,
    detail: str,
):
    with patch(RUN_WORKFLOW, new_callable=AsyncMock) as workflow:
        response = db_client.post(
            "/api/v1/outreach/run",
            json=run_payload(seed, **overrides),
        )

    assert response.status_code == status_code
    assert response.json()["detail"] == detail
    workflow.assert_not_awaited()


def test_product_from_another_seller_is_rejected(
    db_client: TestClient,
    seed: Seed,
):
    with patch(RUN_WORKFLOW, new_callable=AsyncMock) as workflow:
        response = db_client.post(
            "/api/v1/outreach/run",
            json=run_payload(seed, selected_product_id=seed.other_product_id),
        )

    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]
    workflow.assert_not_awaited()


def test_product_without_seller_is_rejected(
    db_client: TestClient,
    seed: Seed,
):
    payload = run_payload(seed)
    del payload["seller_company_id"]

    with patch(RUN_WORKFLOW, new_callable=AsyncMock) as workflow:
        response = db_client.post("/api/v1/outreach/run", json=payload)

    assert response.status_code == 422
    workflow.assert_not_awaited()


def test_rejected_contact_is_refused(
    db_client: TestClient,
    seed: Seed,
):
    with patch(RUN_WORKFLOW, new_callable=AsyncMock) as workflow:
        response = db_client.post(
            "/api/v1/outreach/run",
            json=run_payload(
                seed,
                selected_contact=contact_payload("REJECTED"),
            ),
        )

    assert response.status_code == 422
    workflow.assert_not_awaited()


# --------------------------------------------------
# Human approval
# --------------------------------------------------


def test_passing_draft_can_be_approved(
    db_client: TestClient,
    seed: Seed,
):
    run = create_run(db_client, seed, approved=True)

    response = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["human_approved"] is True
    assert body["review_override"] is False
    assert body["approved_at"] is not None


def test_failed_draft_requires_acknowledgement(
    db_client: TestClient,
    seed: Seed,
):
    run = create_run(db_client, seed, approved=False)

    refused = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")
    assert refused.status_code == 409

    stored = db_client.get(f"/api/v1/outreach/runs/{run['id']}").json()
    assert stored["human_approved"] is False

    accepted = db_client.post(
        f"/api/v1/outreach/runs/{run['id']}/approve",
        json={"acknowledge_failed_review": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["human_approved"] is True
    assert accepted.json()["review_override"] is True


def test_editing_draft_resets_approval(
    db_client: TestClient,
    seed: Seed,
):
    run = create_run(db_client, seed, approved=True)
    db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")

    edited = {
        "subject": "Edited subject line",
        "body": "Hello, this is a human-edited body that is long enough.",
        "call_to_action": "Would a short call help?",
    }
    response = db_client.put(
        f"/api/v1/outreach/runs/{run['id']}/draft",
        json={"email": edited},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["final_email"] == edited
    assert body["human_approved"] is False
    assert body["approved_at"] is None


# --------------------------------------------------
# Gmail drafts
# --------------------------------------------------


def test_gmail_draft_requires_human_approval(
    db_client: TestClient,
    seed: Seed,
):
    run = create_run(db_client, seed, approved=True)

    with patch(CREATE_GMAIL_DRAFT) as create_draft:
        response = db_client.post(
            "/api/v1/gmail/drafts",
            json={"run_id": run["id"], "recipient_email": "me@example.com"},
        )

    assert response.status_code == 403
    create_draft.assert_not_called()


def test_gmail_draft_uses_human_edited_email(
    db_client: TestClient,
    seed: Seed,
):
    run = create_run(db_client, seed, approved=True)

    edited = {
        "subject": "Edited subject line",
        "body": "Hello, this is the human-edited version of the email.",
        "call_to_action": "Would a short call help?",
    }
    db_client.put(
        f"/api/v1/outreach/runs/{run['id']}/draft",
        json={"email": edited},
    )
    db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")

    with patch(
        CREATE_GMAIL_DRAFT,
        return_value={"draft_id": "draft-123", "status": "created"},
    ) as create_draft:
        response = db_client.post(
            "/api/v1/gmail/drafts",
            json={"run_id": run["id"], "recipient_email": "me@example.com"},
        )

    assert response.status_code == 200
    assert response.json()["draft_id"] == "draft-123"

    create_draft.assert_called_once()
    sent_email = create_draft.call_args.kwargs["email"]
    assert sent_email.subject == "Edited subject line"
    assert create_draft.call_args.kwargs["recipient_email"] == "me@example.com"


# --------------------------------------------------
# Re-checking human edits with the AI reviewer
# --------------------------------------------------

AGENT_CALL = "app.workflows.outreach_workflow.Runner.run"

EDITED_EMAIL = {
    "subject": "Customer flow at Example Retail",
    "body": (
        "Hello, Tensator's Call Forward System calls the next customer "
        "to a free service point. Would a short call next week help?"
    ),
    "call_to_action": "Would a short call next week help?",
}


def reviewer_returns(
    *,
    passed: bool,
    flags: list[tuple[str, str]] | None = None,
) -> AsyncMock:
    """Mock the reviewer model. Flags are (quote, problem) pairs."""
    review = make_result(approved=passed).review
    if flags is None:
        flags = [] if passed else [("Tensator's Call Forward System", "Unsupported")]
    output = ReviewerOutput(
        **review.model_dump(exclude={"unsupported_claims", "ignored_claims"}),
        flagged_claims=[FlaggedClaim(quote=q, problem=p, supported=False) for q, p in flags],
    )
    return AsyncMock(
        return_value=type("RunResult", (), {"final_output": output})(),
    )


def edit(db_client: TestClient, run_id: int, email: dict = EDITED_EMAIL) -> dict:
    response = db_client.put(
        f"/api/v1/outreach/runs/{run_id}/draft",
        json={"email": email},
    )
    assert response.status_code == 200, response.text
    return response.json()


def recheck(db_client: TestClient, run_id: int, *, passed: bool) -> tuple[dict, AsyncMock]:
    mock = reviewer_returns(passed=passed)
    with patch(AGENT_CALL, mock):
        response = db_client.post(f"/api/v1/outreach/runs/{run_id}/review")
    assert response.status_code == 200, response.text
    return response.json(), mock


def test_recheck_requires_an_edit(db_client: TestClient, seed: Seed):
    run = create_run(db_client, seed, approved=False)

    with patch(AGENT_CALL, new_callable=AsyncMock) as agent:
        response = db_client.post(f"/api/v1/outreach/runs/{run['id']}/review")

    assert response.status_code == 400
    agent.assert_not_awaited()


def test_recheck_unknown_run(db_client: TestClient, seed: Seed):
    with patch(AGENT_CALL, new_callable=AsyncMock):
        response = db_client.post("/api/v1/outreach/runs/999999/review")

    assert response.status_code == 404


def test_fixed_draft_is_approved_without_override(db_client: TestClient, seed: Seed):
    run = create_run(db_client, seed, approved=False)
    assert run["review_passed"] is False

    edited = edit(db_client, run["id"])
    assert edited["final_review"] is None
    assert edited["review_passed"] is False  # not checked yet

    checked, agent = recheck(db_client, run["id"], passed=True)
    agent.assert_awaited_once()
    assert checked["final_review"]["approved"] is True
    assert checked["review_passed"] is True
    # The AI draft's own review is kept unchanged.
    assert checked["approved"] is False
    assert checked["review"]["unsupported_claims"] == ["Unverified job title"]

    approved = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["human_approved"] is True
    assert approved.json()["review_override"] is False


def test_failed_recheck_still_needs_override(db_client: TestClient, seed: Seed):
    run = create_run(db_client, seed, approved=False)
    edit(db_client, run["id"])

    checked, _ = recheck(db_client, run["id"], passed=False)
    assert checked["review_passed"] is False

    refused = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")
    assert refused.status_code == 409


def test_failed_recheck_overrides_a_passing_ai_draft(db_client: TestClient, seed: Seed):
    """If the human's edits introduce a problem, the latest review wins."""
    run = create_run(db_client, seed, approved=True)
    edit(db_client, run["id"])

    checked, _ = recheck(db_client, run["id"], passed=False)
    assert checked["review_passed"] is False

    refused = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")
    assert refused.status_code == 409


def test_editing_again_clears_the_check(db_client: TestClient, seed: Seed):
    run = create_run(db_client, seed, approved=False)
    edit(db_client, run["id"])
    recheck(db_client, run["id"], passed=True)

    changed = dict(EDITED_EMAIL, subject="A different subject line")
    edited_again = edit(db_client, run["id"], changed)

    assert edited_again["final_review"] is None
    assert edited_again["review_passed"] is False
    refused = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")
    assert refused.status_code == 409


def test_recheck_uses_details_saved_with_the_run(
    db_client: TestClient,
    seed: Seed,
    session_factory: sessionmaker[Session],
):
    """Changing the product later must not change what the re-check sees."""
    run = create_run(db_client, seed, approved=False)

    with session_factory() as session:
        product = session.get(CompanyProduct, seed.product_id)
        product.description = "CHANGED AFTER THE RUN"
        session.commit()

    edit(db_client, run["id"])
    _, agent = recheck(db_client, run["id"], passed=True)

    agent_used, prompt = agent.await_args.args
    assert agent_used.name == "Cold Email Reviewer"
    assert EDITED_EMAIL["body"] in prompt
    # The catalogue is labelled as the evidence for product claims.
    assert '"approved_product_facts": {' in prompt
    assert "Calls the next customer to a free service point." in prompt
    assert "CHANGED AFTER THE RUN" not in prompt
    assert "NOT_VERIFIED" in prompt
    assert "Do not claim that a contact currently holds" in prompt


def test_recheck_run_created_before_context_was_saved(
    db_client: TestClient,
    seed: Seed,
    session_factory: sessionmaker[Session],
):
    result = make_result(approved=False)

    with session_factory() as session:
        old_run = OutreachRun(
            lead_id=seed.lead_id,
            research=result.research.model_dump(mode="json"),
            email=result.email.model_dump(mode="json"),
            review=result.review.model_dump(mode="json"),
            context=None,
            lead_run_number=1,
            approved=False,
            improved=False,
            improvement_count=0,
            requires_human_review=True,
        )
        session.add(old_run)
        session.commit()
        run_id = old_run.id

    edit(db_client, run_id)
    checked, agent = recheck(db_client, run_id, passed=True)

    assert checked["review_passed"] is True
    prompt = agent.await_args.args[1]
    assert "Not recorded for this run." in prompt
    assert "Example Retail" in prompt


def test_wrong_flag_cannot_block_a_fixed_draft(db_client: TestClient, seed: Seed):
    """The Run 08 case: a flag about a job title the email never states."""
    run = create_run(db_client, seed, approved=False)
    edit(db_client, run["id"])

    mock = reviewer_returns(
        passed=True,
        flags=[("as Head of Store Operations", "Job title is unverified")],
    )
    with patch(AGENT_CALL, mock):
        checked = db_client.post(f"/api/v1/outreach/runs/{run['id']}/review").json()

    assert checked["final_review"]["unsupported_claims"] == []
    assert checked["final_review"]["ignored_claims"] == [
        '"as Head of Store Operations": Job title is unverified (quote not found in the email)'
    ]
    assert checked["review_passed"] is True

    approved = db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["review_override"] is False


def test_job_title_never_reaches_the_reviewer(db_client: TestClient, seed: Seed):
    run = create_run(db_client, seed, approved=False)
    edit(db_client, run["id"])
    _, agent = recheck(db_client, run["id"], passed=True)

    prompt = agent.await_args.args[1]
    assert "Jane Doe" in prompt
    assert "reported_job_title" not in prompt
    assert "theorg.com" not in prompt  # source URL stays out too


# --------------------------------------------------
# Run numbers per lead
# --------------------------------------------------


def test_runs_are_numbered_per_lead(
    db_client: TestClient,
    seed: Seed,
    session_factory: sessionmaker[Session],
):
    first = create_run(db_client, seed, approved=True)
    second = create_run(db_client, seed, approved=True)

    with session_factory() as session:
        other = Lead(
            company_name="Other Retail",
            website=None,
            industry="Retail",
            target_role="Operations",
            pain_point="Possible queues",
        )
        session.add(other)
        session.commit()
        other_id = other.id

    with patch(RUN_WORKFLOW, new_callable=AsyncMock, return_value=make_result(approved=True)):
        third = db_client.post(
            "/api/v1/outreach/run",
            json={"lead_id": other_id, "sender_offering": OFFERING},
        ).json()

    assert (first["lead_run_number"], second["lead_run_number"]) == (1, 2)
    assert third["lead_run_number"] == 1  # numbering restarts for each lead
    assert third["id"] > second["id"] > first["id"]  # global number still exists

    recent = db_client.get("/api/v1/outreach/runs").json()
    assert [run["id"] for run in recent][:3] == [third["id"], second["id"], first["id"]]


# --------------------------------------------------
# Editing and deleting leads
# --------------------------------------------------


LEAD_UPDATE = {
    "company_name": "Example Retail Group",
    "website": "https://example.com",
    "industry": "Retail",
    "target_role": "Head of Customer Experience",
    "pain_point": "Possible queues at service desks",
    "recipient_name": None,
    "recipient_email": "ops@example.com",
}


def test_update_lead(db_client: TestClient, seed: Seed):
    response = db_client.put(f"/api/v1/leads/{seed.lead_id}", json=LEAD_UPDATE)

    assert response.status_code == 200
    assert response.json()["company_name"] == "Example Retail Group"
    assert response.json()["target_role"] == "Head of Customer Experience"
    assert db_client.put("/api/v1/leads/999999", json=LEAD_UPDATE).status_code == 404


def test_leads_list_shows_run_count(db_client: TestClient, seed: Seed):
    create_run(db_client, seed, approved=True)
    create_run(db_client, seed, approved=True)

    leads = db_client.get("/api/v1/leads").json()
    lead = next(item for item in leads if item["id"] == seed.lead_id)
    assert lead["run_count"] == 2


def test_delete_lead_also_deletes_its_runs(db_client: TestClient, seed: Seed):
    run = create_run(db_client, seed, approved=True)

    response = db_client.delete(f"/api/v1/leads/{seed.lead_id}")

    assert response.status_code == 204
    assert db_client.get(f"/api/v1/leads/{seed.lead_id}").status_code == 404
    assert db_client.get(f"/api/v1/outreach/runs/{run['id']}").status_code == 404
    assert db_client.delete(f"/api/v1/leads/{seed.lead_id}").status_code == 404


# --------------------------------------------------
# Sender details on the company
# --------------------------------------------------


COMPANY = {
    "name": "Signature Test Co",
    "website": None,
    "industry": "Queue management",
    "description": "Queue management solutions.",
    "target_customers": "Retailers",
    "differentiators": "Hardware",
}


def test_company_saves_sender_details(db_client: TestClient, seed: Seed):
    created = db_client.post(
        "/api/v1/companies",
        json={
            **COMPANY,
            "sender_name": "  Sam Seller ",
            "sender_job_title": "",
            "sender_email": "sam@tensator.example",
            "cta_type": "email",
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["sender_name"] == "Sam Seller"
    assert body["sender_job_title"] is None  # blank becomes empty
    assert body["cta_type"] == "email"


def test_company_rejects_bad_sender_details(db_client: TestClient, seed: Seed):
    bad_email = db_client.post(
        "/api/v1/companies", json={**COMPANY, "sender_email": "not-an-email"}
    )
    bad_cta = db_client.post("/api/v1/companies", json={**COMPANY, "cta_type": "fax"})

    assert bad_email.status_code == 422
    assert bad_cta.status_code == 422
