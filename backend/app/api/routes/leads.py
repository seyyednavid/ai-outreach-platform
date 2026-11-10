
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.lead import Lead
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
    statement = select(Lead).order_by(Lead.id.desc())
    return db.scalars(statement).all()
