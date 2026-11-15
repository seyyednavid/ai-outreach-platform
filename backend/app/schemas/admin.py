from datetime import datetime

from pydantic import BaseModel, computed_field

from app.core.tracing import trace_url


class Me(BaseModel):
    email: str | None
    is_admin: bool


class OrganizationUsage(BaseModel):
    """One customer's AI usage. Totals only, no email content."""

    organization_id: int
    name: str
    user_emails: list[str]
    drafts: int
    approved_drafts: int
    llm_requests: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    last_draft_at: datetime | None


class UsageOverview(BaseModel):
    organizations: list[OrganizationUsage]
    total_drafts: int
    total_tokens: int
    total_estimated_cost_usd: float


class RunUsage(BaseModel):
    """A run as the owner sees it: usage and traces, not the email."""

    id: int
    lead_id: int
    lead_run_number: int
    created_at: datetime
    approved: bool
    human_approved: bool
    llm_requests: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    trace_id: str | None
    recheck_trace_id: str | None

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def trace_url(self) -> str | None:
        return trace_url(self.trace_id)

    @computed_field
    @property
    def recheck_trace_url(self) -> str | None:
        return trace_url(self.recheck_trace_id)
