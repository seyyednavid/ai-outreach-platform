from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.outreach_run import OutreachRun
from app.schemas.lead import LeadCreate
from app.services.ownership import get_owned


def create_lead(
    db: Session,
    organization_id: int,
    lead_data: LeadCreate,
) -> Lead:
    lead = Lead(organization_id=organization_id, **lead_data.model_dump())

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


def get_lead(
    db: Session,
    organization_id: int,
    lead_id: int,
) -> Lead | None:
    return get_owned(db, Lead, organization_id, lead_id)


def update_lead(
    db: Session,
    organization_id: int,
    lead_id: int,
    lead_data: LeadCreate,
) -> Lead | None:
    lead = get_lead(db, organization_id, lead_id)

    if lead is None:
        return None

    for field, value in lead_data.model_dump().items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, organization_id: int, lead_id: int) -> bool:
    """Delete the lead and all of its outreach runs."""
    lead = get_lead(db, organization_id, lead_id)

    if lead is None:
        return False

    db.execute(delete(OutreachRun).where(OutreachRun.lead_id == lead.id))
    db.delete(lead)
    db.commit()
    return True


def list_leads(db: Session, organization_id: int) -> list[Lead]:
    """Newest first, each with `run_count` set for the Leads page."""
    leads = list(
        db.scalars(
            select(Lead)
            .where(Lead.organization_id == organization_id)
            .order_by(Lead.id.desc())
        ).all()
    )

    counts = dict(
        db.execute(
            select(OutreachRun.lead_id, func.count())
            .where(OutreachRun.organization_id == organization_id)
            .group_by(OutreachRun.lead_id)
        ).all()
    )

    for lead in leads:
        lead.run_count = counts.get(lead.id, 0)

    return leads
