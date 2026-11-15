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


class QualityStats(BaseModel):
    """How well the AI and the code checks performed, over all drafts."""

    drafts: int
    # The AI's own draft passed review (score >= 8, no flags left).
    ai_passed: int
    # Passed without any rewrite by the Improver.
    first_try_passed: int
    average_score: float | None
    average_rewrites: float | None
    # Humans changed the email before approving it.
    edited_by_human: int
    edits_checked_by_ai: int
    edits_failed_check: int
    human_approved: int
    # Approved although the latest AI review failed.
    overrides: int
    # Flags left in the final AI reviews, and reviewer flags that code
    # dropped because the quote was not in the email (or was supported).
    flags_kept: int
    flags_ignored_by_code: int
    placeholder_flags: int
    missing_signature_flags: int


class OwnerOverview(BaseModel):
    customers: int
    users: int
    drafts: int
    drafts_last_7_days: int
    total_tokens: int
    estimated_cost_usd: float
    average_cost_per_draft_usd: float | None
    quality: QualityStats


class RunUsage(BaseModel):
    """A run as the owner sees it: usage, score and traces, not the email."""

    id: int
    organization_id: int
    organization_name: str | None = None
    lead_id: int
    lead_run_number: int
    created_at: datetime
    overall_score: float | None = None
    approved: bool
    improvement_count: int
    human_approved: bool
    review_override: bool
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
