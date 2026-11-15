"""
Tracing and cost tracking.

Tracing is disabled in tests (conftest), so nothing is sent to OpenAI;
trace ids, metadata and token totals are still produced and checked.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from test_outreach_api import EDITED_EMAIL, Seed, make_result, run_payload
from test_outreach_api import seed as seed_fixture  # noqa: F401  (fixture)

from app.agents.reviewer_agent import ReviewerOutput
from app.core import tracing
from app.core.config import settings
from app.core.tracing import UsageTotals, run_config
from app.services import outreach_service
from app.workflows import outreach_workflow
from app.workflows.outreach_workflow import run_outreach

AGENT_CALL = "app.workflows.outreach_workflow.Runner.run"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def agent_result(output, input_tokens: int = 1_000, output_tokens: int = 200):
    """A Runner result that reports token usage, like the real SDK."""
    usage = SimpleNamespace(requests=1, input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(final_output=output, context_wrapper=SimpleNamespace(usage=usage))


def reviewer_output(*, passed: bool = True) -> ReviewerOutput:
    review = make_result(approved=passed).review
    return ReviewerOutput(
        **review.model_dump(exclude={"unsupported_claims", "ignored_claims"}),
        flagged_claims=[],
    )


# --------------------------------------------------
# Usage and cost
# --------------------------------------------------


def test_usage_adds_up_and_ignores_results_without_usage():
    usage = UsageTotals()

    usage.add(agent_result("a", 1_000, 100))
    usage.add(agent_result("b", 500, 50))
    usage.add(SimpleNamespace(final_output="no usage reported"))

    assert (usage.requests, usage.input_tokens, usage.output_tokens) == (2, 1_500, 150)


def test_cost_uses_configured_prices():
    usage = UsageTotals(requests=1, input_tokens=2_000_000, output_tokens=1_000_000)

    with (
        patch.object(settings, "llm_input_price_per_million", 0.5),
        patch.object(settings, "llm_output_price_per_million", 2.0),
    ):
        assert usage.estimated_cost_usd == 3.0  # 2 x 0.5 + 1 x 2.0


@pytest.mark.parametrize("include", [True, False])
def test_sensitive_data_setting_reaches_every_agent_call(include: bool):
    with patch.object(settings, "trace_include_sensitive_data", include):
        assert run_config().trace_include_sensitive_data is include


# --------------------------------------------------
# One trace per draft
# --------------------------------------------------


@pytest.mark.anyio
async def test_workflow_runs_in_one_trace_and_counts_tokens():
    result = make_result(approved=True)
    agent = AsyncMock(
        side_effect=[
            agent_result(result.research, 3_000, 400),
            agent_result(result.email, 2_000, 300),
            agent_result(reviewer_output(), 2_500, 100),
        ]
    )

    with (
        patch(AGENT_CALL, agent),
        patch.object(outreach_workflow, "trace", wraps=outreach_workflow.trace) as trace,
    ):
        outcome = await run_outreach(
            company_info="Example Ltd",
            sender_offering="Queue management.",
            metadata={"lead_id": 7, "contact_selected": False},
        )

    # One trace for the whole draft, grouped under its own id.
    trace.assert_called_once()
    assert trace.call_args.args[0] == "Outreach draft"
    assert outcome.trace_id is not None and outcome.trace_id.startswith("trace_")
    assert trace.call_args.kwargs["trace_id"] == outcome.trace_id
    assert trace.call_args.kwargs["group_id"] == outcome.trace_id
    assert trace.call_args.kwargs["metadata"] == {
        "workflow_version": tracing.WORKFLOW_VERSION,
        "lead_id": "7",
        "contact_selected": "False",
    }

    # Every agent call used the shared trace settings.
    assert all("run_config" in call.kwargs for call in agent.await_args_list)

    assert (outcome.llm_requests, outcome.input_tokens, outcome.output_tokens) == (
        3,
        7_500,
        800,
    )


@pytest.mark.anyio
async def test_each_draft_gets_its_own_trace():
    def results():
        result = make_result(approved=True)
        return [
            agent_result(result.research),
            agent_result(result.email),
            agent_result(reviewer_output()),
        ]

    with patch(AGENT_CALL, AsyncMock(side_effect=results() + results())):
        first = await run_outreach(company_info="A", sender_offering="Queue management.")
        second = await run_outreach(company_info="B", sender_offering="Queue management.")

    assert first.trace_id != second.trace_id


# --------------------------------------------------
# Saved with the run, visible to the owner only
# --------------------------------------------------

USAGE_FIELDS = {
    "trace_id", "trace_url", "recheck_trace_id", "recheck_trace_url",
    "llm_requests", "input_tokens", "output_tokens", "estimated_cost_usd",
}


def owner_runs(db_client: TestClient, organization_id: int) -> list[dict]:
    """The owner's view of a customer's runs (ADMIN_EMAILS = test user)."""
    with patch.object(settings, "admin_emails", "tester@example.com"):
        response = db_client.get(f"/api/v1/admin/organizations/{organization_id}/runs")
    assert response.status_code == 200, response.text
    return response.json()


def test_run_saves_trace_and_cost_for_the_owner_only(
    db_client: TestClient, seed_fixture: Seed  # noqa: F811
):
    result = make_result(approved=True).model_copy(
        update={
            "trace_id": "trace_0123456789abcdef0123456789abcdef",
            "llm_requests": 4,
            "input_tokens": 10_000,
            "output_tokens": 2_000,
        }
    )

    with (
        patch("app.api.routes.outreach.run_outreach", new_callable=AsyncMock, return_value=result) as workflow,
        patch.object(settings, "llm_input_price_per_million", 0.40),
        patch.object(settings, "llm_output_price_per_million", 1.60),
    ):
        response = db_client.post("/api/v1/outreach/run", json=run_payload(seed_fixture))

    # The customer sees the draft, not tokens, costs or traces.
    assert response.status_code == 200, response.text
    assert USAGE_FIELDS.isdisjoint(response.json())
    assert "estimated_ai_cost_usd" not in db_client.get("/api/v1/dashboard/stats").json()

    # The owner sees them.
    [run] = owner_runs(db_client, seed_fixture.organization_id)
    assert run["trace_url"] == (
        "https://platform.openai.com/traces/trace?trace_id="
        "trace_0123456789abcdef0123456789abcdef"
    )
    assert (run["llm_requests"], run["input_tokens"], run["output_tokens"]) == (4, 10_000, 2_000)
    assert run["estimated_cost_usd"] == pytest.approx(0.0072)  # 0.004 + 0.0032
    assert "email" not in run and "research" not in run  # usage only, no content

    # The trace is labelled with who and what, never with email text.
    metadata = workflow.await_args.kwargs["metadata"]
    assert metadata["lead_id"] == seed_fixture.lead_id
    assert metadata["product_selected"] is True


def test_edit_check_joins_the_drafts_trace_group_and_adds_tokens(
    db_client: TestClient, seed_fixture: Seed  # noqa: F811
):
    result = make_result(approved=False).model_copy(
        update={"trace_id": "trace_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "input_tokens": 1_000,
                "output_tokens": 100, "llm_requests": 3}
    )
    with patch("app.api.routes.outreach.run_outreach", new_callable=AsyncMock, return_value=result):
        run = db_client.post("/api/v1/outreach/run", json=run_payload(seed_fixture)).json()
    [before] = owner_runs(db_client, seed_fixture.organization_id)

    db_client.put(f"/api/v1/outreach/runs/{run['id']}/draft", json={"email": EDITED_EMAIL})

    with (
        patch(AGENT_CALL, AsyncMock(return_value=agent_result(reviewer_output(), 2_000, 50))),
        patch.object(outreach_service, "trace", wraps=outreach_service.trace) as trace,
    ):
        db_client.post(f"/api/v1/outreach/runs/{run['id']}/review")

    [after] = owner_runs(db_client, seed_fixture.organization_id)
    assert trace.call_args.args[0] == "Check human edits"
    assert trace.call_args.kwargs["group_id"] == "trace_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert after["recheck_trace_id"] == trace.call_args.kwargs["trace_id"]
    assert after["recheck_trace_url"].endswith(after["recheck_trace_id"])
    assert (after["llm_requests"], after["input_tokens"], after["output_tokens"]) == (4, 3_000, 150)
    assert after["estimated_cost_usd"] > before["estimated_cost_usd"]


# --------------------------------------------------
# Owner pages
# --------------------------------------------------


def test_customers_cannot_open_owner_pages(db_client: TestClient, test_user):
    with patch.object(settings, "admin_emails", "owner@example.com"):
        me = db_client.get("/api/v1/me").json()
        usage = db_client.get("/api/v1/admin/usage")
        runs = db_client.get(f"/api/v1/admin/organizations/{test_user.organization_id}/runs")

    assert me == {"email": "tester@example.com", "is_admin": False}
    assert (usage.status_code, runs.status_code) == (404, 404)


def test_owner_sees_usage_per_customer(
    db_client: TestClient, seed_fixture: Seed, other_user  # noqa: F811
):
    result = make_result(approved=True).model_copy(
        update={"trace_id": "trace_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "llm_requests": 3,
                "input_tokens": 5_000, "output_tokens": 500}
    )
    with patch("app.api.routes.outreach.run_outreach", new_callable=AsyncMock, return_value=result):
        db_client.post("/api/v1/outreach/run", json=run_payload(seed_fixture))
        db_client.post("/api/v1/outreach/run", json=run_payload(seed_fixture))

    with patch.object(settings, "admin_emails", " Tester@Example.com , someone@else.com"):
        me = db_client.get("/api/v1/me").json()
        usage = db_client.get("/api/v1/admin/usage").json()

    assert me["is_admin"] is True
    by_org = {org["organization_id"]: org for org in usage["organizations"]}

    mine = by_org[seed_fixture.organization_id]
    assert mine["user_emails"] == ["tester@example.com"]
    assert (mine["drafts"], mine["input_tokens"], mine["output_tokens"]) == (2, 10_000, 1_000)

    # Customers without drafts are listed with zero usage.
    other = by_org[other_user.organization_id]
    assert (other["drafts"], other["estimated_cost_usd"]) == (0, 0)

    assert usage["total_drafts"] == 2
    assert usage["total_tokens"] == 11_000


def test_owner_overview_counts_quality_and_guardrails(
    db_client: TestClient, seed_fixture: Seed  # noqa: F811
):
    passed = make_result(approved=True).model_copy(
        update={"trace_id": "trace_cccccccccccccccccccccccccccccccc", "llm_requests": 3,
                "input_tokens": 4_000, "output_tokens": 400}
    )
    failed = make_result(approved=False).model_copy(update={"improvement_count": 2})

    with patch("app.api.routes.outreach.run_outreach", new_callable=AsyncMock, return_value=passed):
        good = db_client.post("/api/v1/outreach/run", json=run_payload(seed_fixture)).json()
    with patch("app.api.routes.outreach.run_outreach", new_callable=AsyncMock, return_value=failed):
        bad = db_client.post("/api/v1/outreach/run", json=run_payload(seed_fixture)).json()

    db_client.post(f"/api/v1/outreach/runs/{good['id']}/approve")
    db_client.post(
        f"/api/v1/outreach/runs/{bad['id']}/approve", json={"acknowledge_failed_review": True}
    )

    with patch.object(settings, "admin_emails", "tester@example.com"):
        overview = db_client.get("/api/v1/admin/overview").json()
        runs = db_client.get("/api/v1/admin/runs").json()

    quality = overview["quality"]
    assert overview["drafts"] == 2
    assert (quality["ai_passed"], quality["first_try_passed"]) == (1, 1)
    assert quality["average_rewrites"] == 1.0
    assert (quality["human_approved"], quality["overrides"]) == (2, 1)
    assert quality["flags_kept"] == 1  # the failed draft's remaining flag
    # Only the run with recorded usage counts towards cost per draft.
    assert overview["average_cost_per_draft_usd"] == pytest.approx(overview["estimated_cost_usd"])

    assert [run["id"] for run in runs] == [bad["id"], good["id"]]
    assert runs[0]["organization_name"] == "Test org"
    assert runs[0]["review_override"] is True
    assert USAGE_FIELDS - {"trace_url", "recheck_trace_url"} <= set(runs[0])
