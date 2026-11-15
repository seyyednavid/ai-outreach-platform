import logging
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import AuthNotConfigured, AuthServiceUnavailable, verify_access_token
from app.core.database import get_db
from app.services.user_service import CurrentUser, get_or_create_user

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> CurrentUser:
    """The one place where every protected request is authenticated."""
    if credentials is None:
        raise unauthorized("Sign in to continue")

    try:
        claims = verify_access_token(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
    except AuthNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail="Login is not configured on the server (SUPABASE_URL)",
        ) from exc
    except AuthServiceUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not reach the login service. Try again shortly.",
        ) from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        logger.info("Rejected access token: %s", exc)
        raise unauthorized("Your session has expired. Sign in again.") from exc

    return get_or_create_user(db, user_id, claims.get("email"))


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
