"""Check Supabase access tokens. No Supabase secret is needed."""

from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import settings

# Supabase signs user tokens with this audience.
AUDIENCE = "authenticated"


class AuthNotConfigured(Exception):
    """SUPABASE_URL is missing from the backend settings."""


class AuthServiceUnavailable(Exception):
    """Supabase's public signing keys could not be downloaded."""


def issuer() -> str:
    if not settings.supabase_url:
        raise AuthNotConfigured
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def jwks_client(jwks_url: str) -> PyJWKClient:
    # Keys are cached in memory, so Supabase is not called on every request.
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600, timeout=5)


def verify_access_token(token: str) -> dict:
    """Return the token's claims, or raise jwt.InvalidTokenError."""
    expected_issuer = issuer()
    algorithm = jwt.get_unverified_header(token).get("alg")

    if algorithm in ("ES256", "RS256"):
        try:
            key = jwks_client(
                f"{expected_issuer}/.well-known/jwks.json"
            ).get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthServiceUnavailable from exc
    elif algorithm == "HS256" and settings.supabase_jwt_secret:
        key = settings.supabase_jwt_secret
    else:
        raise jwt.InvalidTokenError(f"Unsupported signing algorithm: {algorithm}")

    return jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience=AUDIENCE,
        issuer=expected_issuer,
        options={"require": ["exp", "sub", "aud", "iss"]},
    )
