import os
import uuid
from collections.abc import Callable, Generator

import pytest
from agents import set_tracing_disabled
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# Register SQLAlchemy models
import app.models
from app.api.deps import get_current_user
from app.core.database import Base, create_database_engine, get_db
from app.main import app
from app.models.organization import Organization
from app.models.user import User
from app.services.user_service import CurrentUser

# Tests never send traces to OpenAI. Trace ids are still generated.
set_tracing_disabled(True)

# --------------------------------------------------
# Test database configuration
# --------------------------------------------------

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://outreach:local_dev_password@127.0.0.1:5433/outreach_test_db",
)

# Safety: never run tests against the development DB
database_name = make_url(TEST_DATABASE_URL).database

if database_name != "outreach_test_db":
    raise RuntimeError("Tests must use outreach_test_db!")


# Same settings as the app's engine (e.g. hidden query parameters).
test_engine = create_database_engine(TEST_DATABASE_URL)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
)


# --------------------------------------------------
# Database setup
# --------------------------------------------------


@pytest.fixture(scope="session")
def setup_test_database():
    # Start clean, so a crashed earlier run cannot leave old tables.
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def db_engine(setup_test_database):
    """The test database engine (built like the app's engine)."""
    return test_engine


@pytest.fixture
def session_factory(setup_test_database) -> sessionmaker[Session]:
    """Open sessions on the test database to seed or clean records."""
    return TestSessionLocal


# --------------------------------------------------
# Signed-in users (login is replaced, never called)
# --------------------------------------------------

TEST_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
OTHER_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")


@pytest.fixture(scope="session")
def test_users(setup_test_database) -> tuple[CurrentUser, CurrentUser]:
    """Two users in two separate organisations."""
    with TestSessionLocal() as session:
        orgs = [Organization(name="Test org"), Organization(name="Other org")]
        session.add_all(orgs)
        session.flush()

        users = [
            User(id=TEST_USER_ID, email="tester@example.com", organization_id=orgs[0].id),
            User(id=OTHER_USER_ID, email="other@example.com", organization_id=orgs[1].id),
        ]
        session.add_all(users)
        session.commit()

        first, second = (
            CurrentUser(id=u.id, email=u.email, organization_id=u.organization_id)
            for u in users
        )
        return first, second


@pytest.fixture
def test_user(test_users) -> CurrentUser:
    return test_users[0]


@pytest.fixture
def other_user(test_users) -> CurrentUser:
    return test_users[1]


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
    test_user: CurrentUser,
) -> Generator[TestClient, None, None]:
    """A client signed in as test_user."""

    def override_get_db() -> Generator[Session, None, None]:
        with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def act_as(db_client: TestClient) -> Callable[[CurrentUser | None], None]:
    """Switch db_client to another user, or to nobody (None)."""

    def switch(user: CurrentUser | None) -> None:
        if user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = lambda: user

    return switch


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


@pytest.fixture
def clean_db(setup_test_database):
    """
    Delete everything a test created (runs, products, companies, leads).
    The two shared test users and their organisations are kept.
    """
    yield

    from app.models.company import Company
    from app.models.company_product import CompanyProduct
    from app.models.lead import Lead
    from app.models.outreach_run import OutreachRun

    with TestSessionLocal() as session:
        for model in (OutreachRun, CompanyProduct, Company, Lead):
            session.query(model).delete()
        session.commit()
