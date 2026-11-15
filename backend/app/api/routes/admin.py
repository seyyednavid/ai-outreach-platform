from fastapi import APIRouter, HTTPException

from app.api.deps import AdminUser, AuthUser, DbSession
from app.models.organization import Organization
from app.schemas.admin import Me, RunUsage, UsageOverview
from app.services import admin_service
from app.services.user_service import is_admin

router = APIRouter(tags=["Account and owner"])


@router.get("/me", response_model=Me)
def me(user: AuthUser):
    """Who is signed in, and whether to show the owner's Usage page."""
    return Me(email=user.email, is_admin=is_admin(user.email))


@router.get("/admin/usage", response_model=UsageOverview)
def usage(db: DbSession, admin: AdminUser):
    """Tokens and estimated cost per customer. Owners only."""
    return admin_service.usage_overview(db)


@router.get(
    "/admin/organizations/{organization_id}/runs",
    response_model=list[RunUsage],
)
def organization_runs(organization_id: int, db: DbSession, admin: AdminUser):
    """A customer's latest runs with their traces. No email content."""
    if db.get(Organization, organization_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return admin_service.organization_runs(db, organization_id)
