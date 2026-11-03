
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Dedicated database for automated tests
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://outreach:local_dev_password@localhost:5433/outreach_test_db",
)

# Prevent accidentally testing against the development DB
assert TEST_DATABASE_URL.rsplit("/", 1)[-1] == "outreach_test_db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Import models so SQLAlchemy registers the tables
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db():
        with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_leads():
    yield

    from app.models.lead import Lead

    with TestSessionLocal() as session:
        session.query(Lead).delete()
        session.commit()
