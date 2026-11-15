from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings, settings
from app.core.database import get_db
from app.main import app, create_app


def test_health_check(client: TestClient):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_database_answers(db_client: TestClient, act_as):
    act_as(None)  # no login needed

    response = db_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_not_ready_when_database_is_down(client: TestClient):
    broken = MagicMock()
    broken.execute.side_effect = OperationalError("SELECT 1", {}, Exception("down"))
    app.dependency_overrides[get_db] = lambda: broken

    try:
        response = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


def test_cors_origins_are_parsed():
    configured = Settings(cors_origins=" https://app.example.com/ , https://www.example.com ")

    assert configured.cors_origin_list == ["https://app.example.com", "https://www.example.com"]


def test_deployed_frontend_is_allowed_and_others_are_not():
    with patch.object(settings, "cors_origins", "https://app.example.com"):
        client = TestClient(create_app())

    def preflight(origin: str):
        return client.options(
            "/api/v1/health",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        ).headers.get("access-control-allow-origin")

    assert preflight("https://app.example.com") == "https://app.example.com"
    assert preflight("http://localhost:5173") == "http://localhost:5173"
    assert preflight("https://evil.example.net") is None
