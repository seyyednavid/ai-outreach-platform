
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


def is_valid_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


class ContactDiscoveryRequest(BaseModel):
    lead_id: int = Field(gt=0)


class ContactCandidate(BaseModel):
    name: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    relevance_reason: str = Field(min_length=1)

    source_url: str
    source_excerpt: str = Field(min_length=1)

    public_work_email: str | None = None
    email_source_url: str | None = None

    @model_validator(mode="after")
    def validate_sources(self):
        if not is_valid_https_url(self.source_url):
            raise ValueError(
                "Contact source must be a valid HTTPS URL"
            )

        if (
            self.email_source_url is not None
            and not is_valid_https_url(self.email_source_url)
        ):
            raise ValueError(
                "Email source must be a valid HTTPS URL"
            )

        if self.public_work_email is not None:
            email = self.public_work_email.strip()

            if (
                not email
                or email.count("@") != 1
                or any(char.isspace() for char in email)
                or self.email_source_url is None
            ):
                raise ValueError(
                    "A public work email requires a valid-looking "
                    "email address and a public evidence URL"
                )

            self.public_work_email = email

        return self


class ContactDiscoveryResult(BaseModel):
    contacts: list[ContactCandidate] = Field(
        default_factory=list,
        max_length=5,
    )
    search_summary: str
    limitations: list[str] = Field(default_factory=list)


class ReviewedContact(ContactCandidate):
    relevance_score: int
    evidence_status: str
    evidence_warnings: list[str]


class ContactDiscoveryResponse(BaseModel):
    lead_id: int
    target_company: str
    contacts: list[ReviewedContact]
    search_summary: str
    limitations: list[str]

