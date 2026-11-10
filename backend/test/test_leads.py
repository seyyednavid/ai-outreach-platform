
import pytest
from fastapi.testclient import TestClient

VALID_LEAD = {
    "company_name": "Waitrose",
    "website": "https://www.waitrose.com",
    "industry": "Retail",
    "target_role": "Store Operations Manager",
    "pain_point": "Long checkout queues",
    "recipient_name": "Sarah",
    "recipient_email": "sarah@example.com",
}


@pytest.fixture(autouse=True)
def cleanup_leads(clean_leads):
    yield


def test_create_lead_success(db_client: TestClient):
    response = db_client.post(
        "/api/v1/leads",
        json=VALID_LEAD,
    )

    assert response.status_code == 201

    data = response.json()

    assert isinstance(data["id"], int)
    assert data["company_name"] == "Waitrose"
    assert data["recipient_email"] == "sarah@example.com"


def test_get_lead_success(db_client: TestClient):
    create_response = db_client.post(
        "/api/v1/leads",
        json=VALID_LEAD,
    )

    assert create_response.status_code == 201

    lead_id = create_response.json()["id"]

    response = db_client.get(
        f"/api/v1/leads/{lead_id}"
    )

    assert response.status_code == 200
    assert response.json()["company_name"] == "Waitrose"


def test_get_lead_not_found(db_client: TestClient):
    response = db_client.get(
        "/api/v1/leads/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_create_lead_invalid_email(db_client: TestClient):
    invalid_lead = {
        **VALID_LEAD,
        "recipient_email": "not-an-email",
    }

    response = db_client.post(
        "/api/v1/leads",
        json=invalid_lead,
    )

    assert response.status_code == 422


def test_create_lead_missing_company(db_client: TestClient):
    invalid_lead = {
        **VALID_LEAD,
    }

    del invalid_lead["company_name"]

    response = db_client.post(
        "/api/v1/leads",
        json=invalid_lead,
    )

    assert response.status_code == 422
