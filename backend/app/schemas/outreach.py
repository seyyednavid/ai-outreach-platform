
from datetime import datetime

from pydantic import BaseModel, Field

from app.agents.research_agent import ResearchReport
from app.agents.reviewer_agent import EmailReview
from app.agents.writer_agent import EmailDraft


class OutreachRunRequest(BaseModel):
    lead_id: int = Field(gt=0)
    sender_offering: str = Field(min_length=10, max_length=2000)


class OutreachDraftUpdate(BaseModel):
    email: EmailDraft


class OutreachRunResponse(BaseModel):
    id: int
    lead_id: int

    research: ResearchReport
    email: EmailDraft
    final_email: EmailDraft | None
    review: EmailReview

    approved: bool
    improved: bool
    improvement_count: int
    requires_human_review: bool

    human_approved: bool
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
