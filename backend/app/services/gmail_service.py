import base64
import json
import logging
import secrets
import time
import uuid
from email.message import EmailMessage

import requests
from cryptography.fernet import Fernet, InvalidToken
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from sqlalchemy.orm import Session

from app.agents.writer_agent import EmailDraft
from app.core.config import settings
from app.models.gmail_connection import GmailConnection

# Logs say WHY a Gmail step failed (Google's error code, HTTP status, the
# user's id). Never the OAuth code, state, tokens or email content.
logger = logging.getLogger(__name__)

# OAuth permission required for Gmail draft creation.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
]

# Temporary OAuth requests:
# state -> (creation_time, code_verifier, user who started the flow)
# In memory, so this assumes a single backend process.
pending_states: dict[str, tuple[float, str, uuid.UUID]] = {}

STATE_LIFETIME_SECONDS = 600


class GmailNotConfigured(Exception):
    """TOKEN_ENCRYPTION_KEY is missing or invalid."""


class GmailNotConnected(ValueError):
    """This user has no valid Gmail connection. The message is safe to show."""


class GoogleUnavailable(Exception):
    """Google could not be reached. The message is safe to show."""


def token_cipher() -> Fernet:
    """Encrypts Gmail tokens before they are stored in the database."""
    if not settings.token_encryption_key:
        raise GmailNotConfigured("TOKEN_ENCRYPTION_KEY is not set on the server")

    try:
        return Fernet(settings.token_encryption_key.encode())
    except ValueError as exc:
        raise GmailNotConfigured("TOKEN_ENCRYPTION_KEY is not a valid key") from exc


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


def get_authorization_url(user_id: uuid.UUID) -> str:
    """Generate the Google consent URL with PKCE protection."""
    token_cipher()  # Fail before the user goes to Google, not after.

    flow = create_flow()

    now = time.time()

    # Remove expired OAuth requests.
    for state, (created_at, _, _) in list(pending_states.items()):
        if now - created_at > STATE_LIFETIME_SECONDS:
            pending_states.pop(state, None)

    # State protects the OAuth callback against CSRF and tells the
    # callback which user the Gmail account belongs to.
    state = secrets.token_urlsafe(32)

    # PKCE verifier must be preserved until the callback.
    code_verifier = secrets.token_urlsafe(64)
    flow.code_verifier = code_verifier

    pending_states[state] = (now, code_verifier, user_id)

    authorization_url, _ = flow.authorization_url(
        state=state,
        access_type="offline",
        prompt="consent",
        code_challenge_method="S256",
    )

    return authorization_url


def save_credentials(
    db: Session,
    user_id: uuid.UUID,
    credentials: Credentials,
) -> None:
    encrypted = token_cipher().encrypt(credentials.to_json().encode()).decode()

    connection = db.get(GmailConnection, user_id)

    if connection is None:
        db.add(GmailConnection(user_id=user_id, encrypted_token=encrypted))
    else:
        connection.encrypted_token = encrypted

    db.commit()


def exchange_authorization_code(
    db: Session,
    code: str,
    state: str,
) -> None:
    """Exchange Google's authorization code for the user's tokens."""
    pending = pending_states.pop(state, None)

    if pending is None:
        # Never issued, already used, or lost when the server restarted
        # (the pending requests live in memory).
        logger.warning("Gmail connection failed: unknown or already used OAuth state")
        raise ValueError("Invalid or expired OAuth state")

    created_at, code_verifier, user_id = pending

    age = time.time() - created_at
    if age > STATE_LIFETIME_SECONDS:
        logger.warning(
            "Gmail connection failed for user %s: OAuth state expired after %d s",
            user_id,
            age,
        )
        raise ValueError("Expired OAuth state")

    flow = create_flow()

    # Restore the original PKCE verifier.
    flow.code_verifier = code_verifier

    # Google validates the verifier and returns credentials.
    try:
        flow.fetch_token(code=code)
    except OAuth2Error as exc:
        # exc.error is Google's error code, e.g. "invalid_grant".
        logger.warning(
            "Gmail connection failed for user %s: Google refused the token exchange "
            "(error=%s, status=%s)",
            user_id,
            exc.error,
            exc.status_code,
        )
        raise ValueError("Google did not accept the sign-in. Connect Gmail again.") from exc
    except requests.RequestException as exc:
        logger.warning(
            "Gmail connection failed for user %s: could not reach Google (%s)",
            user_id,
            type(exc).__name__,
        )
        raise GoogleUnavailable("Could not reach Google. Try connecting Gmail again.") from exc
    except Warning as exc:
        # oauthlib raises Warning when Google granted other permissions
        # than requested: the user unticked "create drafts" on the
        # consent screen. The Warning carries the token, so it is not logged.
        logger.warning(
            "Gmail connection failed for user %s: the Gmail permission was not granted",
            user_id,
        )
        raise ValueError(
            "The Gmail permission was not granted. Connect again and allow creating drafts."
        ) from exc

    credentials = flow.credentials

    if not credentials.refresh_token:
        logger.warning(
            "Gmail connection failed for user %s: Google returned no refresh token",
            user_id,
        )
        raise ValueError("Google did not return a refresh token")

    save_credentials(db, user_id, credentials)
    logger.info("Gmail connected for user %s", user_id)


def get_credentials(
    db: Session,
    user_id: uuid.UUID,
) -> Credentials | None:
    """Load this user's credentials and refresh an expired access token."""
    connection = db.get(GmailConnection, user_id)

    if connection is None:
        return None

    try:
        info = json.loads(
            token_cipher().decrypt(connection.encrypted_token.encode())
        )
    except InvalidToken:
        # Encrypted with a different key: the user must connect again.
        logger.warning(
            "Stored Gmail token for user %s cannot be decrypted "
            "(TOKEN_ENCRYPTION_KEY changed?); the user must reconnect",
            user_id,
        )
        return None

    credentials = Credentials.from_authorized_user_info(
        info,
        scopes=GMAIL_SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError:
            # Access was revoked in the Google account.
            logger.info(
                "Gmail access for user %s was revoked or expired; the user must reconnect",
                user_id,
            )
            return None

        save_credentials(db, user_id, credentials)

    return credentials


def is_gmail_connected(db: Session, user_id: uuid.UUID) -> bool:
    """Check whether this user has valid Gmail credentials."""
    credentials = get_credentials(db, user_id)

    return bool(credentials and credentials.valid)


def create_gmail_draft(
    db: Session,
    user_id: uuid.UUID,
    recipient_email: str,
    email: EmailDraft,
) -> dict:
    """Create a Gmail draft in this user's account without sending it."""

    credentials = get_credentials(db, user_id)

    if credentials is None or not credentials.valid:
        raise GmailNotConnected("Gmail is not connected")

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
