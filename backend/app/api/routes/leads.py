
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.lead import LeadCreate, LeadResponse
from app.services import lead_service

router = APIRouter(prefix="/leads", tags=["Leads"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lead(
    lead: LeadCreate,
    db: DbSession,
):
    return lead_service.create_lead(
        db=db,
        lead_data=lead,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
)
def get_lead(
    lead_id: int,
    db: DbSession,
):
    lead = lead_service.get_lead(
        db=db,
        lead_id=lead_id,
    )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return lead


@router.get("", response_model=list[LeadResponse])
def list_leads(db: DbSession):
    return lead_service.list_leads(db)


@router.put(
    "/{lead_id}",
    response_model=LeadResponse,
)
def update_lead(
    lead_id: int,
    lead: LeadCreate,
    db: DbSession,
):
    updated = lead_service.update_lead(db=db, lead_id=lead_id, lead_data=lead)

    if updated is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    return updated


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_lead(
    lead_id: int,
    db: DbSession,
):
    """Delete the lead and all of its outreach runs. Cannot be undone."""
    if not lead_service.delete_lead(db=db, lead_id=lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
