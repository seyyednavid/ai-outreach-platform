
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def create_database_engine(url: str) -> Engine:
    """The app's engine settings. The tests build their engine here too."""
    return create_engine(
        url,
        pool_pre_ping=True,
        # Error messages leave out the query's values: they can be email
        # text, contact names or encrypted Gmail tokens, and errors are logged.
        hide_parameters=True,
        # Without a timeout, "localhost" can hang forever on Windows:
        # it tries IPv6 (::1) first, which Docker does not listen on.
        # Prefer 127.0.0.1 in DATABASE_URL to avoid the 5 s fallback.
        connect_args={"connect_timeout": 5},
    )


engine = create_database_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
