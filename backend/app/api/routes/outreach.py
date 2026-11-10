
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.outreach import (
    OutreachDraftUpdate,
    OutreachRunRequest,
    OutreachRunResponse,
)
from app.services import lead_service, outreach_service
from app.workflows.outreach_workflow import run_outreach

router = APIRouter(prefix="/outreach", tags=["Outreach"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/run", response_model=OutreachRunResponse)
async def run_outreach_for_lead(
    request: OutreachRunRequest,
    db: DbSession,
):
    lead = lead_service.get_lead(db, request.lead_id)

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    company_info = (
        f"Company: {lead.company_name}\n"
        f"Website: {lead.website or 'Not provided'}\n"
        f"Industry: {lead.industry}\n"
        f"Target Role: {lead.target_role}\n"
        f"Potential Pain Point: {lead.pain_point}\n"
        f"Recipient: {lead.recipient_name or 'Not provided'}\n"
        "Research the company using public sources. "
        "Treat potential pain points as unverified."
    )

    result = await run_outreach(
        company_info=company_info,
        sender_offering=request.sender_offering,
    )

    saved_run = outreach_service.save_outreach_run(
        db=db,
        lead_id=lead.id,
        result=result,
    )

    return saved_run


@router.get(
    "/runs/{run_id}",
    response_model=OutreachRunResponse,
)
def get_run(run_id: int, db: DbSession):
    run = outreach_service.get_outreach_run(db, run_id)

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return run


@router.get(
    "/leads/{lead_id}/runs",
    response_model=list[OutreachRunResponse],
)
def get_lead_runs(lead_id: int, db: DbSession):
    lead = lead_service.get_lead(db, lead_id)

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    return outreach_service.list_outreach_runs(db, lead_id)



@router.put(
    "/runs/{run_id}/draft",
    response_model=OutreachRunResponse,
)
def update_outreach_draft(
    run_id: int,
    request: OutreachDraftUpdate,
    db: DbSession,
):
    run = outreach_service.update_draft(
        db=db,
        run_id=run_id,
        email=request.email,
    )

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return run


@router.post(
    "/runs/{run_id}/approve",
    response_model=OutreachRunResponse,
)
def approve_outreach_draft(
    run_id: int,
    db: DbSession,
):
    run = outreach_service.approve_draft(
        db=db,
        run_id=run_id,
    )

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return run

