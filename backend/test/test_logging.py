"""
Structured logging: JSON lines for Cloud Logging, redaction of secrets,
safe error descriptions, and hidden SQL parameters.
"""

import io
import json
import logging
from datetime import datetime

import httpx
import openai
import pytest
from agents.exceptions import ModelBehaviorError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.database import engine as app_engine
from app.core.logging_config import (
    HANDLER_NAME,
    QUIET_LOGGERS,
    UVICORN_LOGGERS,
    describe_exception,
    redact,
    setup_logging,
    use_json_logs,
)


@pytest.fixture
def restore_logging():
    """Undo setup_logging() changes, so other tests see the usual setup."""
    names = (None, *UVICORN_LOGGERS, *QUIET_LOGGERS)
    saved = {
        name: (list(lg.handlers), lg.level, lg.propagate)
        for name in names
        for lg in [logging.getLogger(name)]
    }
    yield
    for name, (handlers, level, propagate) in saved.items():
        lg = logging.getLogger(name)
        lg.handlers[:] = handlers
        lg.setLevel(level)
        lg.propagate = propagate


def json_lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


# --------------------------------------------------
# JSON format for Cloud Logging
# --------------------------------------------------


def test_json_entry_has_cloud_logging_fields(restore_logging):
    stream = io.StringIO()
    setup_logging(json_format=True, stream=stream)

    logging.getLogger("app.example").warning("Lead %s skipped", 42)

    [entry] = json_lines(stream)
    assert entry["severity"] == "WARNING"
    assert entry["message"] == "Lead 42 skipped"
    assert entry["logger"] == "app.example"
    assert datetime.fromisoformat(entry["time"]).tzinfo is not None
    location = entry["logging.googleapis.com/sourceLocation"]
    assert location["function"] == "test_json_entry_has_cloud_logging_fields"


def test_traceback_stays_in_one_entry(restore_logging):
    stream = io.StringIO()
    setup_logging(json_format=True, stream=stream)

    try:
        raise ZeroDivisionError("division by zero")
    except ZeroDivisionError:
        logging.getLogger("app.example").exception("Run failed")

    # One line on stdout = one entry in Cloud Logging, traceback included.
    [entry] = json_lines(stream)
    assert entry["severity"] == "ERROR"
    assert entry["message"].startswith("Run failed\nTraceback")
    assert "ZeroDivisionError" in entry["message"]


def test_uvicorn_logs_become_json(restore_logging):
    stream = io.StringIO()
    setup_logging(json_format=True, stream=stream)

    logging.getLogger("uvicorn.error").error("Exception in ASGI application")

    [entry] = json_lines(stream)
    assert entry["logger"] == "uvicorn.error"
    assert entry["severity"] == "ERROR"
    for name in ("uvicorn", "uvicorn.error"):
        assert logging.getLogger(name).handlers == []
        assert logging.getLogger(name).propagate is True


def test_disabled_access_log_stays_disabled(restore_logging):
    # What uvicorn does for UVICORN_ACCESS_LOG=false / --no-access-log.
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False

    setup_logging(json_format=True, stream=io.StringIO())

    assert access.propagate is False
    assert not access.hasHandlers()


def test_enabled_access_log_becomes_json(restore_logging):
    # What uvicorn does when the access log is on (local default).
    access = logging.getLogger("uvicorn.access")
    access.handlers[:] = [logging.StreamHandler(io.StringIO())]
    access.propagate = False
    stream = io.StringIO()

    setup_logging(json_format=True, stream=stream)
    access.info('127.0.0.1 - "GET /api/v1/health HTTP/1.1" 200')

    [entry] = json_lines(stream)
    assert entry["logger"] == "uvicorn.access"


def test_setup_twice_keeps_one_handler(restore_logging):
    setup_logging(json_format=True, stream=io.StringIO())
    setup_logging(json_format=True, stream=io.StringIO())

    ours = [h for h in logging.getLogger().handlers if h.get_name() == HANDLER_NAME]
    assert len(ours) == 1


def test_text_format_locally_is_also_redacted(restore_logging):
    stream = io.StringIO()
    setup_logging(json_format=False, stream=stream)

    logging.getLogger("app.example").info("Calling with Bearer abc.def.ghi")

    assert stream.getvalue().strip() == "INFO      app.example: Calling with Bearer <redacted>"


def test_http_client_noise_is_quiet(restore_logging):
    setup_logging(json_format=True, stream=io.StringIO())

    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, False),
        ({"K_SERVICE": "ai-outreach-backend"}, True),
        ({"CLOUD_RUN_JOB": "ai-outreach-migrate"}, True),
        ({"K_SERVICE": "ai-outreach-backend", "LOG_FORMAT": "text"}, False),
        ({"LOG_FORMAT": "json"}, True),
    ],
)
def test_json_only_on_cloud_run_unless_overridden(monkeypatch, env, expected):
    for name in ("K_SERVICE", "CLOUD_RUN_JOB", "LOG_FORMAT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    assert use_json_logs() is expected


# --------------------------------------------------
# Redaction: the last line of defence
# --------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        ("Authorization: Bearer abc.DEF-123_xyz", "abc.DEF-123_xyz"),
        ("token eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIxMjMifQ.c2lnbmF0dXJl", "eyJhbGciOiJFUzI1NiJ9"),
        ("key sk-proj-AbCdEf123456789", "sk-proj-AbCdEf123456789"),
        ("key sb_secret_AbCdEf123456", "sb_secret_AbCdEf123456"),
        ("access ya29.a0AfH6SMBx-secret", "ya29.a0AfH6SMBx-secret"),
        ("refresh 1//0gAbCdEfGhIjKlMnOp", "1//0gAbCdEfGhIjKlMnOp"),
        ("postgresql+psycopg://postgres.ref:S3cret!pw@pooler.supabase.com:5432/postgres", "S3cret!pw"),
        ("dsn host=db password=S3cret!pw user=x", "S3cret!pw"),
        ("GET /api/v1/gmail/callback?state=st4te-value&code=4/0Ab-code-value&scope=x", "4/0Ab-code-value"),
        ("GET /api/v1/gmail/callback?state=st4te-value&code=abc", "st4te-value"),
        ('{"token": "ya29-ish", "refresh_token": "plain-refresh-value"}', "plain-refresh-value"),
    ],
)
def test_secrets_are_redacted(raw: str, secret: str):
    assert secret not in redact(raw)


def test_redaction_keeps_ordinary_text():
    message = "Gmail API refused the draft for run 12: HTTP 403, reasons=insufficientPermissions"
    assert redact(message) == message


# --------------------------------------------------
# Safe error descriptions
# --------------------------------------------------


def test_error_description_leaves_out_the_message():
    try:
        raise ModelBehaviorError("Invalid JSON: Dear Jane, our confidential offer")
    except ModelBehaviorError as exc:
        description = describe_exception(exc)

    assert description.startswith("ModelBehaviorError raised in test_logging.py:")
    assert "Dear Jane" not in description


def test_error_description_includes_openai_status_and_request_id():
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
        headers={"x-request-id": "req_123"},
    )
    exc = openai.RateLimitError("Rate limit for key sk-proj-AbCdEf123456789", response=response, body=None)

    description = describe_exception(exc)

    assert description == "RateLimitError status=429 request_id=req_123"


# --------------------------------------------------
# Database errors never show the query's values
# --------------------------------------------------


def test_app_engine_hides_query_parameters():
    assert app_engine.hide_parameters is True


def test_database_error_hides_query_values(db_engine):
    # Fails with "division by zero". Without hide_parameters, SQLAlchemy
    # appends "[parameters: {'value': 'Dear Jane, ...'}]" to the error.
    with db_engine.connect() as connection, pytest.raises(DBAPIError) as caught:
        connection.execute(
            text("SELECT CAST(:value AS text), 1 / 0"),
            {"value": "Dear Jane, confidential email text"},
        )

    message = str(caught.value)
    assert "division by zero" in message
    assert "Dear Jane" not in message
    assert "parameters hidden" in message
