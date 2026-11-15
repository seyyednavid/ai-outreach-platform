
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.agents.research_agent import ResearchReport
from app.agents.reviewer_agent import EmailReview
from app.agents.writer_agent import EmailDraft
from app.workflows.outreach_workflow import latest_review_passed


class SelectedContact(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)

    source_url: str = Field(min_length=1)
    evidence_status: Literal[
        "VERIFIED",
        "NEEDS_REVIEW",
        "EXCERPT_CONSISTENT",
        "REJECTED",
    ]

    @model_validator(mode="after")
    def validate_contact(self):
        if self.evidence_status == "REJECTED":
            raise ValueError(
                "Rejected contacts cannot be used in outreach"
            )

        return self


class OutreachRunRequest(BaseModel):
    lead_id: int = Field(gt=0)

    sender_offering: str = Field(
        min_length=10,
        max_length=2000,
    )

    seller_company_id: int | None = Field(
        default=None,
        gt=0,
    )

    selected_product_id: int | None = Field(
        default=None,
        gt=0,
    )

    selected_contact: SelectedContact | None = None

    @model_validator(mode="after")
    def validate_product_selection(self):
        if (
            self.selected_product_id is not None
            and self.seller_company_id is None
        ):
            raise ValueError(
                "seller_company_id is required when "
                "selected_product_id is provided"
            )

        return self


class OutreachDraftUpdate(BaseModel):
    email: EmailDraft


class OutreachApprovalRequest(BaseModel):
    # Required when the final AI review failed: the human
    # explicitly confirms they checked the flagged issues.
    acknowledge_failed_review: bool = False


# Detail fields are optional: runs created before 15 Nov 2026
# stored only the id and name.


class RunSellerSnapshot(BaseModel):
    id: int
    name: str
    industry: str | None = None
    description: str | None = None
    target_customers: str | None = None
    differentiators: str | None = None
    # Signature details. Kept for the record, never sent to the AI.
    sender_name: str | None = None
    sender_job_title: str | None = None
    sign_off: str | None = None
    sender_email: str | None = None
    sender_phone: str | None = None
    cta_type: str | None = None


class RunProductSnapshot(BaseModel):
    id: int
    name: str
    description: str | None = None
    features: list[str] | None = None
    use_cases: list[str] | None = None


class RunContactSnapshot(BaseModel):
    name: str
    reported_job_title: str
    source_url: str
    client_evidence_status: str
    backend_verification_status: Literal["NOT_VERIFIED"]


class OutreachRunContext(BaseModel):
    """Audit snapshot of what the AI workflow was given."""

    sender_offering: str
    seller_company: RunSellerSnapshot | None = None
    selected_product: RunProductSnapshot | None = None
    selected_contact: RunContactSnapshot | None = None


class OutreachRunResponse(BaseModel):
    id: int
    lead_id: int
    # Run 1, 2, 3 ... within the lead; `id` is the global number.
    lead_run_number: int

    research: ResearchReport
    email: EmailDraft
    final_email: EmailDraft | None
    review: EmailReview
    # AI review of final_email, when the human asked for one.
    final_review: EmailReview | None
    context: OutreachRunContext | None

    # True when the AI's own draft passed review.
    approved: bool
    improved: bool
    improvement_count: int
    requires_human_review: bool

    human_approved: bool
    review_override: bool
    approved_at: datetime | None
    created_at: datetime

    # Tokens, costs and traces are owner data: see /admin routes.
    model_config = {"from_attributes": True}

    @computed_field
    @property
    def review_passed(self) -> bool:
        """The review that decides approval: of the edits if checked."""
        return latest_review_passed(
            self.approved,
            self.final_email.model_dump() if self.final_email else None,
            self.final_review.model_dump() if self.final_review else None,
        )
