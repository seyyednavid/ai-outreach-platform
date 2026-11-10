import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# Register SQLAlchemy models
import app.models
from app.core.database import Base, get_db
from app.main import app

# --------------------------------------------------
# Test database configuration
# --------------------------------------------------

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://outreach:local_dev_password@localhost:5433/outreach_test_db",
)

# Safety: never run tests against the development DB
database_name = make_url(TEST_DATABASE_URL).database

if database_name != "outreach_test_db":
    raise RuntimeError("Tests must use outreach_test_db!")


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
)


# --------------------------------------------------
# Database setup
# --------------------------------------------------


@pytest.fixture(scope="session")
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


# --------------------------------------------------
# Client without database (Health Test)
# --------------------------------------------------


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


# --------------------------------------------------
# Client connected to test database
# --------------------------------------------------


@pytest.fixture
def db_client(
    setup_test_database,
) -> Generator[TestClient, None, None]:

    def override_get_db() -> Generator[Session, None, None]:
        with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# --------------------------------------------------
# Clean test records after each database test
# --------------------------------------------------


@pytest.fixture
def clean_leads(setup_test_database):
    yield

    from app.models.lead import Lead

    with TestSessionLocal() as session:
        session.query(Lead).delete()
        session.commit()
