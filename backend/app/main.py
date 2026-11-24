
import logging

from agents import set_default_openai_key
from agents.exceptions import AgentsException
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAIError

from app.api.routes.admin import router as admin_router
from app.api.routes.companies import router as companies_router
from app.api.routes.contact_discovery import router as contact_discovery_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.gmail import router as gmail_router
from app.api.routes.health import router as health_router
from app.api.routes.leads import router as leads_router
from app.api.routes.matching import router as matching_router
from app.api.routes.outreach import router as outreach_router
from app.core.config import settings
from app.core.logging_config import describe_exception, setup_logging

logger = logging.getLogger(__name__)

AI_FAILED_DETAIL = "The AI service failed. Try again in a moment."


async def ai_service_failed(request: Request, exc: Exception) -> JSONResponse:
    """
    An OpenAI or agent error. Logged as type, status and location only:
    the message itself can quote model output, such as email text.
    """
    logger.error(
        "AI request failed: %s %s: %s",
        request.method,
        request.url.path,
        describe_exception(exc),
    )
    return JSONResponse(status_code=502, content={"detail": AI_FAILED_DETAIL})


def create_app() -> FastAPI:
    setup_logging()
    set_default_openai_key(settings.openai_api_key)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        # Deployed frontends come from CORS_ORIGINS. Local development is
        # always allowed: Vite moves to 5174+ when 5173 is busy.
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(leads_router, prefix="/api/v1")
    app.include_router(outreach_router, prefix="/api/v1")
    app.include_router(gmail_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(companies_router, prefix="/api/v1")
    app.include_router(matching_router, prefix="/api/v1")
    app.include_router(contact_discovery_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")

    # AI calls that fail answer 502 with a readable message, not a bare 500.
    app.add_exception_handler(AgentsException, ai_service_failed)
    app.add_exception_handler(OpenAIError, ai_service_failed)

    return app


app = create_app()
