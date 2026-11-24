"""
Gmail OAuth failures: every failure is logged with a reason, and the
OAuth code, state and tokens never reach the logs. The browser always
gets a readable page, never a bare 500 or 422.
"""

import logging
import time
import uuid
from types import SimpleNamespace

import pytest
import requests
from fastapi.testclient import TestClient
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from app.services import gmail_service
from app.services.gmail_service import GoogleUnavailable

USER_ID = uuid.UUID("00000000-0000-4000-8000-0000000000aa")
STATE = "state-value-that-must-never-be-logged"
CODE = "4/0Ab-code-value-that-must-never-be-logged"
REFRESH_TOKEN = "1//refresh-token-that-must-never-be-logged"
ACCESS_TOKEN = "ya29.access-token-that-must-never-be-logged"

CALLBACK = "/api/v1/gmail/callback"


class FakeFlow:
    """Stands in for Google's OAuth flow: no network calls."""

    def __init__(self, error: Exception | None = None, refresh_token: str | None = REFRESH_TOKEN):
        self.error = error
        self.code_verifier = None
        self.credentials = SimpleNamespace(refresh_token=refresh_token, token=ACCESS_TOKEN)

    def fetch_token(self, code: str) -> None:
        if self.error:
            raise self.error


@pytest.fixture
def pending_state():
    """A Gmail connection started by USER_ID, waiting for Google's callback."""
    gmail_service.pending_states[STATE] = (time.time(), "pkce-verifier", USER_ID)
    yield
    gmail_service.pending_states.pop(STATE, None)


@pytest.fixture
def use_flow(monkeypatch):
    def install(flow: FakeFlow) -> None:
        monkeypatch.setattr(gmail_service, "create_flow", lambda: flow)

    return install


def assert_nothing_secret_logged(caplog: pytest.LogCaptureFixture) -> None:
    for secret in (STATE, CODE, REFRESH_TOKEN, ACCESS_TOKEN, "pkce-verifier"):
        assert secret not in caplog.text


def exchange() -> None:
    gmail_service.exchange_authorization_code(db=None, code=CODE, state=STATE)


# --------------------------------------------------
# Token exchange (gmail_service)
# --------------------------------------------------


def test_unknown_state_is_logged(caplog):
    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="Invalid or expired OAuth state"):
        exchange()

    assert "unknown or already used OAuth state" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_expired_state_is_logged(caplog):
    gmail_service.pending_states[STATE] = (time.time() - 3600, "pkce-verifier", USER_ID)

    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="Expired OAuth state"):
        exchange()

    assert f"user {USER_ID}: OAuth state expired" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_refused_token_exchange_is_handled(caplog, pending_state, use_flow):
    use_flow(FakeFlow(error=InvalidGrantError(description="Bad Request")))

    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="Google did not accept"):
        exchange()

    assert "error=invalid_grant, status=400" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_google_unreachable_is_handled(caplog, pending_state, use_flow):
    use_flow(FakeFlow(error=requests.ConnectionError(f"Failed: POST /token?code={CODE}")))

    with caplog.at_level(logging.WARNING), pytest.raises(GoogleUnavailable):
        exchange()

    assert "could not reach Google (ConnectionError)" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_missing_gmail_permission_is_handled(caplog, pending_state, use_flow):
    # oauthlib attaches the token to this Warning: it must not be logged.
    warning = Warning("Scope has changed")
    warning.token = {"access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN}
    use_flow(FakeFlow(error=warning))

    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="permission was not granted"):
        exchange()

    assert "the Gmail permission was not granted" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_missing_refresh_token_is_logged(caplog, pending_state, use_flow):
    use_flow(FakeFlow(refresh_token=None))

    with caplog.at_level(logging.WARNING), pytest.raises(ValueError, match="no refresh token|did not return"):
        exchange()

    assert "Google returned no refresh token" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_successful_connection_is_logged_without_tokens(caplog, pending_state, use_flow, monkeypatch):
    saved = []
    monkeypatch.setattr(gmail_service, "save_credentials", lambda db, user_id, credentials: saved.append(user_id))
    use_flow(FakeFlow())

    with caplog.at_level(logging.INFO):
        exchange()

    assert saved == [USER_ID]
    assert f"Gmail connected for user {USER_ID}" in caplog.text
    assert_nothing_secret_logged(caplog)


# --------------------------------------------------
# Callback page (route)
# --------------------------------------------------


@pytest.fixture
def exchange_raises(monkeypatch):
    def install(error: Exception | None) -> None:
        def fake_exchange(db, code, state):
            if error:
                raise error

        monkeypatch.setattr(gmail_service, "exchange_authorization_code", fake_exchange)

    return install


def test_callback_success_page_is_unchanged(client: TestClient, exchange_raises):
    exchange_raises(None)

    response = client.get(CALLBACK, params={"code": CODE, "state": STATE})

    assert response.status_code == 200
    assert "Gmail connected" in response.text


def test_callback_failure_shows_reason(client: TestClient, exchange_raises):
    exchange_raises(ValueError("Invalid or expired OAuth state"))

    response = client.get(CALLBACK, params={"code": CODE, "state": STATE})

    assert response.status_code == 400
    assert "Invalid or expired OAuth state" in response.text


def test_callback_when_google_is_unreachable(client: TestClient, exchange_raises):
    exchange_raises(GoogleUnavailable("Could not reach Google. Try connecting Gmail again."))

    response = client.get(CALLBACK, params={"code": CODE, "state": STATE})

    assert response.status_code == 502
    assert "Could not reach Google" in response.text


def test_cancelled_consent_shows_a_page(client: TestClient, caplog, exchange_raises):
    exchange_raises(AssertionError("must not be called"))

    with caplog.at_level(logging.WARNING):
        response = client.get(CALLBACK, params={"error": "access_denied", "state": STATE})

    # Before: 422 JSON, because "code" was required.
    assert response.status_code == 400
    assert "Google did not grant access" in response.text
    assert "error=access_denied" in caplog.text
    assert_nothing_secret_logged(caplog)


def test_error_value_is_cleaned_before_logging(client: TestClient, caplog):
    with caplog.at_level(logging.WARNING):
        client.get(CALLBACK, params={"error": "access_denied\nFAKE LOG LINE <script>"})

    assert "error=access_deniedFAKELOGLINEscript" in caplog.text
    assert "\nFAKE" not in caplog.text


def test_callback_without_code_shows_a_page(client: TestClient):
    response = client.get(CALLBACK, params={"state": STATE})

    assert response.status_code == 400
    assert "incomplete" in response.text
