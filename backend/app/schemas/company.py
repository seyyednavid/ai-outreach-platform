
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    industry: str = Field(min_length=1)
    description: str = Field(min_length=1)
    target_customers: str = Field(min_length=1)
    differentiators: str = Field(min_length=1)

    # Email signature and call to action. Optional so existing
    # companies keep working; drafts without a sender name fail review.
    sender_name: str | None = Field(default=None, max_length=200)
    sender_job_title: str | None = Field(default=None, max_length=200)
    sign_off: str | None = Field(default=None, max_length=100)
    sender_email: EmailStr | None = None
    sender_phone: str | None = Field(default=None, max_length=50)
    cta_type: Literal["call", "email"] = "call"

    @field_validator(
        "sender_name",
        "sender_job_title",
        "sign_off",
        "sender_phone",
        "sender_email",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class CompanyResponse(CompanyCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    features: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)


class ProductResponse(ProductCreate):
    id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)
