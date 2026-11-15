"""
Login and data isolation.

Tokens are signed in the test with a throwaway key; Supabase is never
called. Agents and Gmail are mocked.
"""

import time
import uuid
from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker
from test_outreach_api import EDITED_EMAIL, make_result

from app.core import auth
from app.core.config import settings
from app.models.company import Company
from app.models.company_product import CompanyProduct
from app.models.lead import Lead
from app.models.organization import Organization
from app.models.outreach_run import OutreachRun
from app.models.user import User
from app.services.user_service import CurrentUser

SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"

SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())
WRONG_KEY = ec.generate_private_key(ec.SECP256R1())


class FakeJwksClient:
    """Stands in for Supabase's public key endpoint."""

    def get_signing_key_from_jwt(self, token):
        class Key:
            key = SIGNING_KEY.public_key()

        return Key()


def make_token(
    user_id: uuid.UUID,
    email: str = "someone@example.com",
    *,
    key=SIGNING_KEY,
    **overrides,
) -> str:
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "email": email,
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 600,
        **overrides,
    }
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "test"})


@pytest.fixture
def real_login(
    act_as: Callable[[CurrentUser | None], None],
) -> Generator[None, None, None]:
    """Use the real token check, with Supabase replaced by a local key."""
    act_as(None)
    with (
        patch.object(settings, "supabase_url", SUPABASE_URL),
        patch.object(auth, "jwks_client", lambda url: FakeJwksClient()),
    ):
        yield


@pytest.fixture
def cleanup(session_factory: sessionmaker[Session]) -> Generator[None, None, None]:
    yield
    with session_factory() as session:
        session.query(OutreachRun).delete()
        session.query(CompanyProduct).delete()
        session.query(Company).delete()
        session.query(Lead).delete()
        # Keep the two shared test users and their organisations.
        session.execute(delete(User).where(User.email.ilike("new-%")))
        session.execute(
            delete(Organization).where(
                Organization.name.not_in(["Test org", "Other org"])
            )
        )
        session.commit()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------
# Token checks
# --------------------------------------------------


def test_request_without_token_is_rejected(db_client: TestClient, act_as):
    act_as(None)

    response = db_client.get("/api/v1/leads")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_health_needs_no_login(db_client: TestClient, act_as):
    act_as(None)

    assert db_client.get("/api/v1/health").status_code == 200


def test_valid_token_is_accepted(db_client: TestClient, real_login, test_user):
    response = db_client.get(
        "/api/v1/leads",
        headers=auth_header(make_token(test_user.id, "tester@example.com")),
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "token_kwargs",
    [
        {"key": WRONG_KEY},  # forged signature
        {"exp": int(time.time()) - 60},  # expired
        {"aud": "anon"},  # not a signed-in user token
        {"iss": "https://other-project.supabase.co/auth/v1"},  # another project
    ],
    ids=["wrong-key", "expired", "wrong-audience", "wrong-issuer"],
)
def test_bad_tokens_are_rejected(db_client: TestClient, real_login, test_user, token_kwargs):
    response = db_client.get(
        "/api/v1/leads",
        headers=auth_header(make_token(test_user.id, **token_kwargs)),
    )

    assert response.status_code == 401


def test_shared_secret_tokens_need_a_configured_secret(
    db_client: TestClient, real_login, test_user
):
    token = jwt.encode(
        {"sub": str(test_user.id), "aud": "authenticated", "iss": ISSUER,
         "exp": int(time.time()) + 600},
        "a-guessed-secret-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )

    response = db_client.get("/api/v1/leads", headers=auth_header(token))

    assert response.status_code == 401


def test_missing_supabase_url_is_a_server_error(db_client: TestClient, act_as, test_user):
    act_as(None)

    with patch.object(settings, "supabase_url", None):
        response = db_client.get(
            "/api/v1/leads",
            headers=auth_header(make_token(test_user.id)),
        )

    assert response.status_code == 503


# --------------------------------------------------
# First sign-in
# --------------------------------------------------


def test_first_sign_in_creates_user_and_organisation(
    db_client: TestClient,
    real_login,
    cleanup,
    session_factory: sessionmaker[Session],
):
    new_id = uuid.uuid4()
    token = make_token(new_id, "new-person@example.com")

    first = db_client.get("/api/v1/leads", headers=auth_header(token))
    again = db_client.get("/api/v1/leads", headers=auth_header(token))

    assert first.status_code == again.status_code == 200
    assert first.json() == []  # starts empty, sees nobody else's leads

    with session_factory() as session:
        user = session.get(User, new_id)
        assert user is not None
        assert user.email == "new-person@example.com"
        org_users = session.scalars(
            select(User).where(User.organization_id == user.organization_id)
        ).all()
        assert len(org_users) == 1


def test_legacy_owner_receives_existing_data(
    db_client: TestClient,
    real_login,
    cleanup,
    session_factory: sessionmaker[Session],
):
    with session_factory() as session:
        legacy = Organization(name="My organisation")
        session.add(legacy)
        session.flush()
        session.add(
            Lead(
                organization_id=legacy.id,
                company_name="Lead From Before Login",
                website=None,
                industry="Retail",
                target_role="Operations",
                pain_point="Queues",
            )
        )
        session.commit()

    stranger = make_token(uuid.uuid4(), "new-stranger@example.com")
    owner = make_token(uuid.uuid4(), "New-Owner@Example.com")

    with patch.object(settings, "legacy_owner_email", "new-owner@example.com"):
        stranger_leads = db_client.get("/api/v1/leads", headers=auth_header(stranger))
        owner_leads = db_client.get("/api/v1/leads", headers=auth_header(owner))

    assert stranger_leads.json() == []
    assert [lead["company_name"] for lead in owner_leads.json()] == [
        "Lead From Before Login"
    ]


# --------------------------------------------------
# Isolation: one organisation never sees another's data
# --------------------------------------------------

COMPANY = {
    "name": "Owner Co",
    "website": None,
    "industry": "Queue management",
    "description": "Queue management solutions.",
    "target_customers": "Retailers",
    "differentiators": "Hardware",
    "sender_name": "Owner Person",
}
PRODUCT = {
    "name": "Owner Product",
    "description": "A product.",
    "features": ["One"],
    "use_cases": ["Two"],
}
LEAD = {
    "company_name": "Owner Lead",
    "website": None,
    "industry": "Retail",
    "target_role": "Operations",
    "pain_point": "Queues",
    "recipient_name": None,
    "recipient_email": None,
}


@pytest.fixture
def owned(db_client: TestClient, cleanup) -> dict[str, int]:
    """A company, product, lead and approved run owned by test_user."""
    company = db_client.post("/api/v1/companies", json=COMPANY).json()
    product = db_client.post(
        f"/api/v1/companies/{company['id']}/products", json=PRODUCT
    ).json()
    lead = db_client.post("/api/v1/leads", json=LEAD).json()

    with patch(
        "app.api.routes.outreach.run_outreach",
        new_callable=AsyncMock,
        return_value=make_result(approved=True),
    ):
        run = db_client.post(
            "/api/v1/outreach/run",
            json={
                "lead_id": lead["id"],
                "sender_offering": "Queue management for retail.",
                "seller_company_id": company["id"],
            },
        ).json()
    db_client.post(f"/api/v1/outreach/runs/{run['id']}/approve")

    return {
        "company": company["id"],
        "product": product["id"],
        "lead": lead["id"],
        "run": run["id"],
    }


def test_other_user_sees_empty_lists(db_client: TestClient, owned, act_as, other_user):
    act_as(other_user)

    assert db_client.get("/api/v1/leads").json() == []
    assert db_client.get("/api/v1/companies").json() == []
    assert db_client.get("/api/v1/outreach/runs").json() == []
    stats = db_client.get("/api/v1/dashboard/stats").json()
    assert stats["total_leads"] == stats["total_outreach_runs"] == 0


def test_other_user_cannot_touch_records(db_client: TestClient, owned, act_as, other_user):
    c, p, lead, run = owned["company"], owned["product"], owned["lead"], owned["run"]
    # A valid email, so only ownership can refuse the edit.
    edited = {**EDITED_EMAIL, "subject": "Hijacked"}

    act_as(other_user)
    attempts = [
        db_client.get(f"/api/v1/companies/{c}"),
        db_client.put(f"/api/v1/companies/{c}", json=COMPANY),
        db_client.get(f"/api/v1/companies/{c}/products"),
        db_client.post(f"/api/v1/companies/{c}/products", json=PRODUCT),
        db_client.put(f"/api/v1/companies/{c}/products/{p}", json=PRODUCT),
        db_client.delete(f"/api/v1/companies/{c}/products/{p}"),
        db_client.get(f"/api/v1/leads/{lead}"),
        db_client.put(f"/api/v1/leads/{lead}", json=LEAD),
        db_client.delete(f"/api/v1/leads/{lead}"),
        db_client.get(f"/api/v1/outreach/leads/{lead}/runs"),
        db_client.get(f"/api/v1/outreach/runs/{run}"),
        db_client.put(f"/api/v1/outreach/runs/{run}/draft", json={"email": edited}),
        db_client.post(f"/api/v1/outreach/runs/{run}/review"),
        db_client.post(
            f"/api/v1/outreach/runs/{run}/approve",
            json={"acknowledge_failed_review": True},
        ),
    ]

    # 404, not 403: other organisations' ids look like missing ones.
    assert [r.status_code for r in attempts] == [404] * len(attempts)


def test_owner_records_survive_other_users_attempts(
    db_client: TestClient, owned, act_as, other_user, test_user
):
    act_as(other_user)
    db_client.delete(f"/api/v1/leads/{owned['lead']}")
    hijack = db_client.put(
        f"/api/v1/outreach/runs/{owned['run']}/draft",
        json={"email": {**EDITED_EMAIL, "subject": "Hijacked"}},
    )
    assert hijack.status_code == 404

    act_as(test_user)
    run = db_client.get(f"/api/v1/outreach/runs/{owned['run']}").json()

    assert db_client.get(f"/api/v1/leads/{owned['lead']}").status_code == 200
    assert run["final_email"] is None
    assert run["human_approved"] is True


def test_agents_never_run_on_other_users_records(
    db_client: TestClient, owned, act_as, other_user
):
    act_as(other_user)

    with (
        patch("app.api.routes.matching.Runner.run", new_callable=AsyncMock) as match,
        patch("app.api.routes.contact_discovery.Runner.run", new_callable=AsyncMock) as find,
        patch("app.api.routes.outreach.run_outreach", new_callable=AsyncMock) as write,
    ):
        responses = [
            db_client.post(
                "/api/v1/matching/preview",
                json={"company_id": owned["company"], "lead_id": owned["lead"]},
            ),
            db_client.post("/api/v1/contacts/discover", json={"lead_id": owned["lead"]}),
            db_client.post(
                "/api/v1/outreach/run",
                json={"lead_id": owned["lead"], "sender_offering": "Anything at all."},
            ),
        ]

    assert [r.status_code for r in responses] == [404, 404, 404]
    match.assert_not_called()
    find.assert_not_called()
    write.assert_not_called()


def test_cannot_use_another_users_company_for_own_lead(
    db_client: TestClient, owned, act_as, other_user
):
    act_as(other_user)
    own_lead = db_client.post("/api/v1/leads", json={**LEAD, "company_name": "Mine"}).json()

    with patch(
        "app.api.routes.outreach.run_outreach", new_callable=AsyncMock
    ) as write:
        response = db_client.post(
            "/api/v1/outreach/run",
            json={
                "lead_id": own_lead["id"],
                "sender_offering": "Queue management for retail.",
                "seller_company_id": owned["company"],
                "selected_product_id": owned["product"],
            },
        )

    assert response.status_code == 404
    write.assert_not_called()


def test_gmail_draft_of_another_users_run_is_refused(
    db_client: TestClient, owned, act_as, other_user
):
    act_as(other_user)

    with patch("app.services.gmail_service.create_gmail_draft") as create_draft:
        response = db_client.post(
            "/api/v1/gmail/drafts",
            json={"run_id": owned["run"], "recipient_email": "me@example.com"},
        )

    assert response.status_code == 404
    create_draft.assert_not_called()
