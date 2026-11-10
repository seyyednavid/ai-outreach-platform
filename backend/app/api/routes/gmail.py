
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from googleapiclient.errors import HttpError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.agents.writer_agent import EmailDraft
from app.core.database import get_db
from app.models.outreach_run import OutreachRun
from app.services import gmail_service

router = APIRouter(prefix="/gmail", tags=["Gmail"])


@router.get("/connect")
def connect_gmail():
    authorization_url = gmail_service.get_authorization_url()

    return RedirectResponse(url=authorization_url)


@router.get("/callback")
def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    try:
        gmail_service.exchange_authorization_code(
            code=code,
            state=state,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "connected",
        "message": "Gmail connected successfully!",
    }


@router.get("/status")
def gmail_status():
    return {
        "connected": gmail_service.is_gmail_connected()
    }


class GmailDraftRequest(BaseModel):
    run_id: int = Field(gt=0)
    recipient_email: EmailStr


@router.post("/drafts")
def create_draft(
    request: GmailDraftRequest,
    db: Annotated[Session, Depends(get_db)],
):
    # Find the outreach run in PostgreSQL.
    run = db.get(OutreachRun, request.run_id)

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
            recipient_email=str(request.recipient_email),
            email=email,
        )
    except ValueError as exc:
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
