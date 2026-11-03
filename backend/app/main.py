from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.leads import router as leads_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(leads_router, prefix="/api/v1")

    return app


app = create_app()
