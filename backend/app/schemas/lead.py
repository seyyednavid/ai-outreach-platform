
from pydantic import BaseModel, EmailStr, Field


class LeadCreate(BaseModel):
    company_name: str = Field(min_length=1)
    website: str | None = None
    industry: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    pain_point: str = Field(min_length=1)
    recipient_name: str | None = None
    recipient_email: EmailStr | None = None


class LeadResponse(LeadCreate):
    id: int
    # Number of outreach runs; deleting the lead deletes them too.
    run_count: int = 0

    model_config = {"from_attributes": True}
