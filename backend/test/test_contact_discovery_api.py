"""Contact discovery: several focused searches, merged and checked in code."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.routes.contact_discovery import SEARCH_FOCUSES
from app.schemas.contact_discovery import ContactCandidate, ContactDiscoveryResult

LEAD = {
    "company_name": "Example Retail",
    "website": "https://example.com",
    "industry": "Retail",
    "target_role": "Store Operations Manager",
    "pain_point": "Possible queues",
    "recipient_name": None,
    "recipient_email": None,
}


def candidate(name: str, title: str) -> ContactCandidate:
    return ContactCandidate(
        name=name,
        job_title=title,
        company_name="Example Retail",
        relevance_reason="Leads store operations.",
        source_url="https://example.com/leadership",
        source_excerpt=f"{name}, {title} at Example Retail.",
    )


def found(*contacts: ContactCandidate, summary: str = "Searched.") -> SimpleNamespace:
    return SimpleNamespace(
        final_output=ContactDiscoveryResult(
            contacts=list(contacts),
            search_summary=summary,
            limitations=["Employment details may be out of date."],
        )
    )


def test_runs_one_search_per_source_and_merges_people(db_client: TestClient, clean_db):
    lead = db_client.post("/api/v1/leads", json=LEAD).json()
    agent = AsyncMock(
        side_effect=[
            found(
                candidate("Jane Doe", "Head of Store Operations"),
                candidate("Customer Service Team", "Customer Service"),  # not a person
                summary="Leadership page.",
            ),
            RuntimeError("search timed out"),  # one failed search is tolerated
            found(candidate("Jane Doe", "Head of Store Operations")),  # duplicate
        ]
    )

    with (
        patch("app.api.routes.contact_discovery.Runner.run", agent),
        patch(
            "app.api.routes.contact_discovery.verify_contact_source",
            new=AsyncMock(side_effect=lambda contact, trusted: contact),
        ),
    ):
        response = db_client.post("/api/v1/contacts/discover", json={"lead_id": lead["id"]})

    body = response.json()
    assert response.status_code == 200, response.text
    assert [contact["name"] for contact in body["contacts"]] == ["Jane Doe"]
    assert body["search_summary"] == "Leadership page."
    assert body["limitations"] == ["Employment details may be out of date."]  # no repeats

    focuses = [json.loads(call.kwargs["input"])["search_focus"] for call in agent.await_args_list]
    assert focuses == list(SEARCH_FOCUSES)


def test_all_searches_failing_is_an_error(db_client: TestClient, clean_db):
    lead = db_client.post("/api/v1/leads", json=LEAD).json()

    with patch(
        "app.api.routes.contact_discovery.Runner.run",
        AsyncMock(side_effect=RuntimeError("down")),
    ):
        response = db_client.post("/api/v1/contacts/discover", json={"lead_id": lead["id"]})

    assert response.status_code == 502
