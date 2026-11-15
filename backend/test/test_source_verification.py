
import pytest

from app.schemas.contact_discovery import ReviewedContact
from app.services import source_verification
from app.services.source_verification import allowed_url


def test_allowed_public_source():
    assert allowed_url(
        "https://www.bizseek.co.uk/marks-spencer"
    )


def test_reject_localhost():
    assert not allowed_url(
        "https://localhost/internal"
    )


def test_reject_private_ip():
    assert not allowed_url(
        "https://127.0.0.1/admin"
    )


def test_reject_http():
    assert not allowed_url(
        "http://www.bizseek.co.uk/marks-spencer"
    )


def test_reject_unapproved_domain():
    assert not allowed_url(
        "https://unapproved.example/profile"
    )


def test_reject_redirect_target_port():
    assert not allowed_url(
        "https://www.bizseek.co.uk:8080/profile"
    )



@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_contact(source_url: str) -> ReviewedContact:
    return ReviewedContact(
        name="Jane Doe",
        job_title="Head of Store Operations",
        company_name="Example Retail",
        relevance_reason="Runs store operations",
        source_url=source_url,
        source_excerpt="Jane Doe, Head of Store Operations",
        public_work_email="jane.doe@example.com",
        email_source_url=source_url,
        relevance_score=40,
        evidence_status="EXCERPT_CONSISTENT",
        evidence_warnings=[],
    )


@pytest.mark.anyio
async def test_unlisted_source_needs_review_not_rejected():
    """A source we cannot check is unverified, not evidence against the contact."""
    result = await source_verification.verify_contact_source(
        make_contact("https://corporate.example.com/leadership")
    )

    assert result.evidence_status == "NEEDS_REVIEW"
    assert result.public_work_email is None
    assert any("allowlist" in warning for warning in result.evidence_warnings)


@pytest.mark.anyio
async def test_unreachable_allowed_source_needs_review(monkeypatch):
    async def no_page(url: str, trusted_domains=()) -> None:
        return None

    monkeypatch.setattr(source_verification, "fetch_page_text", no_page)

    result = await source_verification.verify_contact_source(
        make_contact("https://theorg.com/example/jane-doe")
    )

    assert result.evidence_status == "NEEDS_REVIEW"
    assert result.public_work_email is None


@pytest.mark.anyio
async def test_name_and_role_found_is_verified(monkeypatch):
    async def page(url: str, trusted_domains=()) -> str:
        return "jane doe head of store operations jane.doe@example.com"

    monkeypatch.setattr(source_verification, "fetch_page_text", page)

    result = await source_verification.verify_contact_source(
        make_contact("https://theorg.com/example/jane-doe")
    )

    assert result.evidence_status == "VERIFIED"
    assert result.public_work_email == "jane.doe@example.com"


@pytest.mark.parametrize(
    ("website", "domain"),
    [
        ("https://www.marksandspencer.com", "marksandspencer.com"),
        ("marksandspencer.com", "marksandspencer.com"),
        ("https://shop.example.co.uk/path", "shop.example.co.uk"),
        (None, None),
        ("localhost", None),
    ],
)
def test_site_domain(website, domain):
    assert source_verification.site_domain(website) == domain


def test_lead_domain_and_subdomains_are_checkable():
    trusted = ("marksandspencer.com",)
    url = "https://corporate.marksandspencer.com/about-us/our-leadership"

    assert not source_verification.allowed_url(url)
    assert source_verification.allowed_url(url, trusted)
    assert source_verification.allowed_url("https://marksandspencer.com/x", trusted)
    # Look-alike domains and plain http stay blocked.
    assert not source_verification.allowed_url("https://evilmarksandspencer.com/x", trusted)
    assert not source_verification.allowed_url("http://corporate.marksandspencer.com/x", trusted)
