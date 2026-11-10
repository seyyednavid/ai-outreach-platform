
from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    total_leads: int = Field(ge=0)
    total_outreach_runs: int = Field(ge=0)
    human_approved_emails: int = Field(ge=0)
    average_review_score: float = Field(ge=0, le=10)
