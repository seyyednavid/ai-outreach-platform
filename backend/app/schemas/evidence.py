
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class VerificationStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    NEEDS_REVIEW = "needs_review"


class Evidence(BaseModel):
    claim: str = Field(min_length=1)
    source_url: HttpUrl
    source_excerpt: str = Field(min_length=1)


class VerificationResult(BaseModel):
    evidence: Evidence
    status: VerificationStatus
    explanation: str = Field(min_length=1)
