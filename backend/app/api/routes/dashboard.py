from fastapi import APIRouter

from app.api.deps import AuthUser, DbSession
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_service import get_dashboard_stats

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbSession, user: AuthUser):
    return get_dashboard_stats(db, user.organization_id)
