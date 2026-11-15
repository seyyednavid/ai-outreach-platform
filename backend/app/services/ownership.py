from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.lead import Lead
from app.models.outreach_run import OutreachRun


def get_owned[Owned: (Company, Lead, OutreachRun)](
    db: Session,
    model: type[Owned],
    organization_id: int,
    record_id: int,
) -> Owned | None:
    """
    The record, only if it belongs to this organisation. Records of
    other organisations look exactly like missing ones (404), so ids
    cannot be probed.
    """
    record = db.get(model, record_id)

    if record is None or record.organization_id != organization_id:
        return None

    return record
