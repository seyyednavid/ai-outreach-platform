from fastapi import APIRouter, HTTPException, Query

from app.api.deps import AdminUser, AuthUser, DbSession
from app.models.organization import Organization
from app.schemas.admin import Me, OwnerOverview, RunUsage, UsageOverview
from app.services import admin_service
from app.services.user_service import is_admin

router = APIRouter(tags=["Account and owner"])


@router.get("/me", response_model=Me)
def me(user: AuthUser):
    """Who is signed in, and whether to show the Owner Console."""
    return Me(email=user.email, is_admin=is_admin(user.email))


@router.get("/admin/overview", response_model=OwnerOverview)
def overview(db: DbSession, admin: AdminUser):
    """Customers, drafts, cost and AI quality across the product."""
    return admin_service.owner_overview(db)


@router.get("/admin/usage", response_model=UsageOverview)
def usage(db: DbSession, admin: AdminUser):
    """Tokens and estimated cost per customer."""
    return admin_service.usage_overview(db)


@router.get("/admin/runs", response_model=list[RunUsage])
def runs(
    db: DbSession,
    admin: AdminUser,
    organization_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Latest runs across customers, or for one customer. No email content."""
    if organization_id is not None and db.get(Organization, organization_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return admin_service.recent_runs(db, organization_id, limit)


@router.get(
    "/admin/organizations/{organization_id}/runs",
    response_model=list[RunUsage],
)
def organization_runs(organization_id: int, db: DbSession, admin: AdminUser):
    """A customer's latest runs with their traces."""
    return runs(db, admin, organization_id, 50)
