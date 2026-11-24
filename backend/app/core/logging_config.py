"""
Logging for the backend.

On Cloud Run every log line is one JSON object, which Cloud Logging reads
as a structured entry: "severity" makes errors filterable, and a
traceback stays in the same entry as its message, so Error Reporting can
group it. Locally (Docker Compose, uvicorn --reload) logs stay plain text.

Every line passes through redact(): a last line of defence that removes
tokens, API keys, OAuth codes and database passwords if any code ever
logs one by mistake. Code should still never log them on purpose.
"""

import json
import logging
import os
import re
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

HANDLER_NAME = "app-log-handler"

# Cloud Logging severities that match Python level names one to one.
SEVERITIES = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Chatty libraries: one INFO line per HTTP call is noise, not signal.
QUIET_LOGGERS = ("httpx", "httpcore")

# Uvicorn's own loggers. On Cloud Run they are sent through our handler.
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

APP_ROOT = Path(__file__).resolve().parents[1]

REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    # Authorization: Bearer <token>
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+"), r"\1 <redacted>"),
    # JWTs, e.g. Supabase access tokens
    (re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*"), "<redacted-jwt>"),
    # OpenAI and Supabase secret keys
    (re.compile(r"\bsk-[A-Za-z0-9_*-]{8,}"), "<redacted-key>"),
    (re.compile(r"\bsb_secret_[A-Za-z0-9_-]+"), "<redacted-key>"),
    # Google access and refresh tokens
    (re.compile(r"\bya29\.[A-Za-z0-9._-]+"), "<redacted-token>"),
    (re.compile(r"\b1//[A-Za-z0-9._-]{10,}"), "<redacted-token>"),
    # user:password@ in URLs, e.g. postgresql+psycopg://user:pass@host
    (re.compile(r"(\b[a-z][a-z0-9+.-]*://)[^\s/:@]+:[^\s/@]+@"), r"\1<redacted>@"),
    # password=... in connection strings
    (re.compile(r"(?i)\b(password=)[^\s&]+"), r"\1<redacted>"),
    # OAuth values in URLs: ?code=...&state=...
    (
        re.compile(
            r"(?i)([?&](?:code|state|access_token|refresh_token|id_token|client_secret|token)=)[^&\s\"']+"
        ),
        r"\1<redacted>",
    ),
    # Token fields in JSON, e.g. Google credentials
    (
        re.compile(
            r'(?i)("(?:access_token|refresh_token|id_token|client_secret|token)"\s*:\s*")[^"]+'
        ),
        r"\1<redacted>",
    ),
]


def redact(text: str) -> str:
    """Remove secrets that must never reach the logs."""
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class CloudLoggingFormatter(logging.Formatter):
    """One JSON object per line, in the shape Cloud Logging understands."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        if record.stack_info:
            message = f"{message}\n{self.formatStack(record.stack_info)}"

        entry = {
            "severity": record.levelname if record.levelname in SEVERITIES else "DEFAULT",
            "message": redact(message),
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "logger": record.name,
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }
        return json.dumps(entry, ensure_ascii=False, default=str)


class RedactingFormatter(logging.Formatter):
    """Plain text for local development, with the same redaction."""

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def use_json_logs() -> bool:
    """JSON on Cloud Run, plain text elsewhere. LOG_FORMAT=json|text overrides."""
    choice = os.getenv("LOG_FORMAT", "").strip().lower()
    if choice in ("json", "text"):
        return choice == "json"
    # Cloud Run sets K_SERVICE in services and CLOUD_RUN_JOB in jobs.
    return bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"))


def setup_logging(
    json_format: bool | None = None,
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> None:
    """Send all logs, the app's and uvicorn's, through one handler. Safe to call twice."""
    if json_format is None:
        json_format = use_json_logs()

    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == HANDLER_NAME:
            root.removeHandler(handler)

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(
        CloudLoggingFormatter()
        if json_format
        else RedactingFormatter("%(levelname)-9s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)

    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    if json_format:
        # Uvicorn installs its own plain-text handlers before the app is
        # imported. Remove them so its lines (startup, errors with
        # tracebacks) become JSON entries too.
        for name in UVICORN_LOGGERS:
            uvicorn_logger = logging.getLogger(name)
            if name == "uvicorn.access" and access_log_disabled(uvicorn_logger):
                continue
            uvicorn_logger.handlers.clear()
            uvicorn_logger.propagate = True


def access_log_disabled(access_logger: logging.Logger) -> bool:
    """
    UVICORN_ACCESS_LOG=false (or --no-access-log) leaves uvicorn's access
    logger with no handlers and propagate=False. Uvicorn writes access
    lines only when that logger has somewhere to send them, so routing
    it to our handler would switch the access log back on.
    """
    return not access_logger.handlers and not access_logger.propagate


def describe_exception(exc: BaseException) -> str:
    """
    A safe one-line description of an error: its type, HTTP status and
    request id when it has them, and where it happened. Never the
    message, which can quote model output (email text) or request data.
    """
    parts = [type(exc).__name__]

    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        parts.append(f"status={status}")

    request_id = getattr(exc, "request_id", None)
    if isinstance(request_id, str):
        parts.append(f"request_id={request_id}")

    frames = traceback.extract_tb(exc.__traceback__)
    if frames:
        last = frames[-1]
        parts.append(f"raised in {Path(last.filename).name}:{last.lineno}")

        own = [f for f in frames if Path(f.filename).resolve().is_relative_to(APP_ROOT)]
        if own and own[-1] is not last:
            caller = own[-1]
            relative = Path(caller.filename).resolve().relative_to(APP_ROOT.parent)
            parts.append(f"from {relative.as_posix()}:{caller.lineno}")

    return " ".join(parts)
