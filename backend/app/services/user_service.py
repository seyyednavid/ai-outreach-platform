import uuid
from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.organization import Organization
from app.models.user import User


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None
    organization_id: int


def unclaimed_organization(db: Session) -> Organization | None:
    """The organisation created for data from before login existed."""
    return db.scalar(
        select(Organization)
        .where(~exists().where(User.organization_id == Organization.id))
        .order_by(Organization.id)
        .limit(1)
    )


def is_legacy_owner(email: str | None) -> bool:
    owner = settings.legacy_owner_email
    return bool(email and owner and email.strip().lower() == owner.strip().lower())


def get_or_create_user(
    db: Session,
    user_id: uuid.UUID,
    email: str | None,
) -> CurrentUser:
    """
    Find the signed-in user, or create them on their first request
    together with their own organisation.
    """
    user = db.get(User, user_id)

    if user is None:
        organization = unclaimed_organization(db) if is_legacy_owner(email) else None

        if organization is None:
            organization = Organization(name=email or "My organisation")
            db.add(organization)
            db.flush()

        user = User(id=user_id, email=email, organization_id=organization.id)
        db.add(user)

        try:
            db.commit()
        except IntegrityError:
            # Two first requests arrived together; the other one won.
            db.rollback()
            user = db.get(User, user_id)
            if user is None:
                raise

    return CurrentUser(
        id=user.id,
        email=user.email,
        organization_id=user.organization_id,
    )
