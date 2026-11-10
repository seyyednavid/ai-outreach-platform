
import pytest

from app.agents.research_agent import ResearchFinding
from app.services.source_validator import validate_source


@pytest.mark.parametrize(
    ("source_url", "expected"),
    [
        ("https://www.waitrose.com", True),
        ("http://www.waitrose.com", False),
        ("not-a-url", False),
        ("https:///missing-host", False),
        ("https://user:password@example.com", False),
    ],
)
def test_validate_source(source_url: str, expected: bool):
    finding = ResearchFinding(
        claim="A test company fact",
        source_url=source_url,
    )

    assert validate_source(finding) is expected


def test_validate_source_rejects_empty_claim():
    finding = ResearchFinding(
        claim="   ",
        source_url="https://www.waitrose.com",
    )

    assert validate_source(finding) is False
