from html import escape

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from googleapiclient.errors import HttpError
from pydantic import BaseModel, EmailStr, Field

from app.agents.writer_agent import EmailDraft
from app.api.deps import AuthUser, DbSession
from app.models.outreach_run import OutreachRun
from app.services import gmail_service
from app.services.gmail_service import GmailNotConfigured
from app.services.ownership import get_owned

router = APIRouter(prefix="/gmail", tags=["Gmail"])


def result_page(title: str, message: str, status_code: int = 200) -> HTMLResponse:
    """A small page for the browser tab Google redirects back to."""
    return HTMLResponse(
        status_code=status_code,
        content=(
            "<!doctype html><meta charset='utf-8'>"
            f"<title>{escape(title)}</title>"
            "<body style='font-family:system-ui,sans-serif;max-width:32rem;"
            "margin:4rem auto;padding:0 1rem;line-height:1.5'>"
            f"<h1 style='font-size:1.4rem'>{escape(title)}</h1>"
            f"<p>{escape(message)}</p></body>"
        ),
    )


class GmailConnectResponse(BaseModel):
    authorization_url: str


@router.get("/connect", response_model=GmailConnectResponse)
def connect_gmail(user: AuthUser):
    """
    The Google consent URL for the signed-in user. The browser opens it;
    a plain link cannot be used because it would not carry the login token.
    """
    try:
        url = gmail_service.get_authorization_url(user.id)
    except GmailNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return GmailConnectResponse(authorization_url=url)


@router.get("/callback", response_class=HTMLResponse)
def gmail_callback(
    db: DbSession,
    code: str = Query(...),
    state: str = Query(...),
):
    # No login token here: Google redirects the browser. The one-time
    # state value identifies the user who started the connection.
    try:
        gmail_service.exchange_authorization_code(db=db, code=code, state=state)
    except (ValueError, GmailNotConfigured) as exc:
        return result_page("Gmail was not connected", str(exc), status_code=400)

    return result_page(
        "Gmail connected",
        "You can close this tab and press Recheck in AI Outreach.",
    )


@router.get("/status")
def gmail_status(db: DbSession, user: AuthUser):
    try:
        connected = gmail_service.is_gmail_connected(db, user.id)
    except GmailNotConfigured:
        connected = False

    return {"connected": connected}


class GmailDraftRequest(BaseModel):
    run_id: int = Field(gt=0)
    recipient_email: EmailStr


@router.post("/drafts")
def create_draft(
    request: GmailDraftRequest,
    db: DbSession,
    user: AuthUser,
):
    run = get_owned(db, OutreachRun, user.organization_id, request.run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Outreach run not found",
        )

    # Authorization gate: human approval is mandatory.
    if not run.human_approved:
        raise HTTPException(
            status_code=403,
            detail="Human approval is required",
        )

    # Prefer the human-edited email.
    email_data = (
        run.final_email
        if run.final_email is not None
        else run.email
    )

    email = EmailDraft.model_validate(email_data)

    try:
        result = gmail_service.create_gmail_draft(
            db=db,
            user_id=user.id,
            recipient_email=str(request.recipient_email),
            email=email,
        )
    except (ValueError, GmailNotConfigured) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except HttpError as exc:
        raise HTTPException(
            status_code=502,
            detail="Gmail API could not create the draft",
        ) from exc

    return {
        "run_id": run.id,
        **result,
    }
