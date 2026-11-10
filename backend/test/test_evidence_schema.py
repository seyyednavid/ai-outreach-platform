
import pytest
from pydantic import ValidationError

from app.schemas.evidence import (
    Evidence,
    VerificationResult,
    VerificationStatus,
)


def test_create_verification_result():
    evidence = Evidence(
        claim="Waitrose is part of John Lewis Partnership",
        source_url="https://www.johnlewispartnership.co.uk",
        source_excerpt="Waitrose is part of the John Lewis Partnership.",
    )

    result = VerificationResult(
        evidence=evidence,
        status=VerificationStatus.SUPPORTED,
        explanation="The source excerpt supports the claim.",
    )

    assert result.status == VerificationStatus.SUPPORTED


def test_invalid_verification_status():
    with pytest.raises(ValidationError):
        VerificationResult(
            evidence=Evidence(
                claim="Example claim",
                source_url="https://example.com",
                source_excerpt="Example evidence",
            ),
            status="unknown",
            explanation="Invalid status",
        )
