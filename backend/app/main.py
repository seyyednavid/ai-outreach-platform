
from agents import set_default_openai_key
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.companies import router as companies_router
from app.api.routes.contact_discovery import router as contact_discovery_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.gmail import router as gmail_router
from app.api.routes.health import router as health_router
from app.api.routes.leads import router as leads_router
from app.api.routes.matching import router as matching_router
from app.api.routes.outreach import router as outreach_router
from app.core.config import settings


def create_app() -> FastAPI:
    set_default_openai_key(settings.openai_api_key)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )
    
    app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:5173"],
                allow_credentials=False,
                allow_methods=["GET", "POST", "PUT"],
                allow_headers=["Content-Type"],
            )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(leads_router, prefix="/api/v1")
    app.include_router(outreach_router, prefix="/api/v1")
    app.include_router(gmail_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(companies_router, prefix="/api/v1")
    app.include_router(matching_router, prefix="/api/v1")
    app.include_router(contact_discovery_router,prefix="/api/v1")

    return app


app = create_app()
