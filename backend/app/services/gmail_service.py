
import base64
import json
import os
import secrets
import time
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.agents.writer_agent import EmailDraft
from app.core.config import settings

# OAuth permission required for Gmail draft creation.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
]

# Store tokens outside the project directory.
# On Windows: C:\Users\<username>\AppData\Local\ai-outreach-platform
TOKEN_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home()))
) / "ai-outreach-platform"

TOKEN_PATH = TOKEN_DIR / "gmail_tokens.json"

# Temporary OAuth requests:
# state -> (creation_time, code_verifier)
pending_states: dict[str, tuple[float, str]] = {}

STATE_LIFETIME_SECONDS = 600


def create_flow() -> Flow:
    """Create a Google OAuth flow using backend credentials."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.google_redirect_uri,
        autogenerate_code_verifier=False,
    )


def get_authorization_url() -> str:
    """Generate the Google login URL with PKCE protection."""
    flow = create_flow()

    now = time.time()

    # Remove expired OAuth requests.
    for state, (created_at, _) in list(pending_states.items()):
        if now - created_at > STATE_LIFETIME_SECONDS:
            pending_states.pop(state, None)

    # State protects the OAuth callback against CSRF.
    state = secrets.token_urlsafe(32)

    # PKCE verifier must be preserved until the callback.
    code_verifier = secrets.token_urlsafe(64)
    flow.code_verifier = code_verifier

    pending_states[state] = (now, code_verifier)

    authorization_url, _ = flow.authorization_url(
        state=state,
        access_type="offline",
        prompt="consent",
        code_challenge_method="S256",
    )

    return authorization_url


def exchange_authorization_code(
    code: str,
    state: str,
) -> None:
    """Exchange Google's authorization code for OAuth tokens."""
    pending = pending_states.pop(state, None)

    if pending is None:
        raise ValueError("Invalid or expired OAuth state")

    created_at, code_verifier = pending

    if time.time() - created_at > STATE_LIFETIME_SECONDS:
        raise ValueError("Expired OAuth state")

    flow = create_flow()

    # Restore the original PKCE verifier.
    flow.code_verifier = code_verifier

    # Google validates the verifier and returns credentials.
    flow.fetch_token(code=code)

    credentials = flow.credentials

    if not credentials.refresh_token:
        raise ValueError("Google did not return a refresh token")

    # Create the directory only when saving credentials.
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    # Save access/refresh tokens for future Gmail API calls.
    TOKEN_PATH.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )


def get_credentials() -> Credentials | None:
    """Load stored credentials and refresh an expired access token."""
    if not TOKEN_PATH.exists():
        return None

    info = json.loads(
        TOKEN_PATH.read_text(encoding="utf-8")
    )

    credentials = Credentials.from_authorized_user_info(
        info,
        scopes=GMAIL_SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        TOKEN_PATH.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return credentials


def is_gmail_connected() -> bool:
    """Check whether valid Gmail credentials are available."""
    credentials = get_credentials()

    return bool(credentials and credentials.valid)



def create_gmail_draft(
    recipient_email: str,
    email: EmailDraft,
) -> dict:
    """Create a Gmail draft without sending an email."""

    credentials = get_credentials()

    if credentials is None or not credentials.valid:
        raise ValueError("Gmail is not connected")

    # Build the email message.
    message = EmailMessage()
    message["To"] = recipient_email
    message["Subject"] = email.subject
    message.set_content(email.body)

    # Gmail API expects a base64url-encoded MIME message.
    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    gmail = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

    draft = (
        gmail.users()
        .drafts()
        .create(
            userId="me",
            body={
                "message": {
                    "raw": encoded_message,
                }
            },
        )
        .execute()
    )

    return {
        "draft_id": draft["id"],
        "status": "created",
    }
