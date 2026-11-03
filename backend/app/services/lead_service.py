
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.schemas.lead import LeadCreate


def create_lead(
    db: Session,
    lead_data: LeadCreate,
) -> Lead:
    lead = Lead(**lead_data.model_dump())

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


def get_lead(
    db: Session,
    lead_id: int,
) -> Lead | None:
    return db.get(Lead, lead_id)
