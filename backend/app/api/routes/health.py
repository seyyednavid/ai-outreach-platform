import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Liveness: the process is running. Never touches the database."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check(db: DbSession):
    """
    Readiness: the app can serve requests, so the database answers.
    Docker and cloud platforms use this to hold back traffic.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Readiness check failed: %r", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unreachable"},
        )

    return {"status": "ok", "database": "ok"}
