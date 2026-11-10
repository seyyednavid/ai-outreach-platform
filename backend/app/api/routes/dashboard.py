from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_service import get_dashboard_stats

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbSession):
    return get_dashboard_stats(db)
