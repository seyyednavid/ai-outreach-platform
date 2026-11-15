from fastapi import APIRouter, HTTPException, status

from app.api.deps import AuthUser, DbSession
from app.schemas.lead import LeadCreate, LeadResponse
from app.services import lead_service

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lead(
    lead: LeadCreate,
    db: DbSession,
    user: AuthUser,
):
    return lead_service.create_lead(db, user.organization_id, lead)


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
)
def get_lead(
    lead_id: int,
    db: DbSession,
    user: AuthUser,
):
    lead = lead_service.get_lead(db, user.organization_id, lead_id)

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.get("", response_model=list[LeadResponse])
def list_leads(db: DbSession, user: AuthUser):
    return lead_service.list_leads(db, user.organization_id)


@router.put(
    "/{lead_id}",
    response_model=LeadResponse,
)
def update_lead(
    lead_id: int,
    lead: LeadCreate,
    db: DbSession,
    user: AuthUser,
):
    updated = lead_service.update_lead(db, user.organization_id, lead_id, lead)

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
    user: AuthUser,
):
    """Delete the lead and all of its outreach runs. Cannot be undone."""
    if not lead_service.delete_lead(db, user.organization_id, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
