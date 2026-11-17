# Backend image: FastAPI app, agents, migrations and scripts.
# Secrets are NOT copied in: they come from backend/.env at run time.

FROM python:3.12-slim-bookworm

# uv installs the exact versions from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Never run as root. Files are copied with the right owner, so no
# extra "chown" layer duplicates the whole app.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir /app && chown appuser /app
WORKDIR /app
USER appuser

# 1. Dependencies first: this layer is reused until uv.lock changes,
#    so rebuilding after a code change takes seconds.
COPY --chown=appuser pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. Only what the server needs: the app, and the migrations used by
#    the "migrate" service. Development tools (scripts/, evals/, test/)
#    stay out: the simulation writes demo data and must never be
#    runnable against a production database.
COPY --chown=appuser alembic.ini ./
COPY --chown=appuser alembic ./alembic
COPY --chown=appuser app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
