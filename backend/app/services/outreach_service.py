
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from agents import gen_trace_id, trace
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.research_agent import ResearchReport
from app.agents.writer_agent import EmailDraft
from app.core.tracing import UsageTotals, trace_metadata
from app.models.company import Company
from app.models.company_product import CompanyProduct
from app.models.lead import Lead
from app.models.outreach_run import OutreachRun
from app.schemas.outreach import (
    OutreachRunContext,
    OutreachRunRequest,
    RunContactSnapshot,
    RunProductSnapshot,
    RunSellerSnapshot,
)
from app.services.ownership import get_owned
from app.workflows.outreach_workflow import (
    OutreachResult,
    latest_review_passed,
    review_email,
)

# Used when re-checking runs created before context was recorded.
OFFERING_NOT_RECORDED = "Not recorded for this run."


class OutreachRequestError(Exception):
    """A request that cannot be turned into a workflow run."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FailedReviewNotAcknowledged(Exception):
    """Approval of a draft that failed AI review, without acknowledgement."""


class NothingToRecheck(Exception):
    """A re-check was requested but the human has not edited the draft."""


@dataclass
class PreparedRun:
    company_info: str
    outreach_context: dict[str, object]
    snapshot: OutreachRunContext
    # Added to the email by code. None when no sender name is set.
    signature: str | None = None


SENDER_FIELDS = {
    "sender_name",
    "sender_job_title",
    "sign_off",
    "sender_email",
    "sender_phone",
    "cta_type",
}

MISSING_SIGNATURE_FLAG = (
    '"(no signature)": No sender name. Add your sender details in '
    "My Company and choose your company before generating."
)


def seller_snapshot(seller: Company) -> RunSellerSnapshot:
    return RunSellerSnapshot(
        id=seller.id,
        name=seller.name,
        industry=seller.industry,
        description=seller.description,
        target_customers=seller.target_customers,
        differentiators=seller.differentiators,
        sender_name=seller.sender_name,
        sender_job_title=seller.sender_job_title,
        sign_off=seller.sign_off,
        sender_email=seller.sender_email,
        sender_phone=seller.sender_phone,
        cta_type=seller.cta_type,
    )


def build_signature(seller: RunSellerSnapshot | None) -> str | None:
    """
    The sign-off block added to every email, for example:

        Best regards,
        Jane Smith
        Sales Manager, Tensator
        +44 20 0000 0000 · jane@tensator.com
    """
    if seller is None or not seller.sender_name:
        return None

    sign_off = (seller.sign_off or "Best regards").rstrip(",")
    title_line = ", ".join(
        part for part in (seller.sender_job_title, seller.name) if part
    )
    contact_line = " · ".join(
        part for part in (seller.sender_phone, seller.sender_email) if part
    )

    lines = [f"{sign_off},", seller.sender_name, title_line, contact_line]
    return "\n".join(line for line in lines if line)


def flag_missing_signature(
    result: OutreachResult,
    signature: str | None,
) -> OutreachResult:
    """A draft without a signature can never pass review."""
    if signature is not None:
        return result

    review = result.review.model_copy(
        update={
            "unsupported_claims": [
                *result.review.unsupported_claims,
                MISSING_SIGNATURE_FLAG,
            ],
        },
    )
    return result.model_copy(update={"review": review, "approved": False})


def product_snapshot(product: CompanyProduct) -> RunProductSnapshot:
    return RunProductSnapshot(
        id=product.id,
        name=product.name,
        description=product.description,
        features=list(product.features),
        use_cases=list(product.use_cases),
    )


def build_agent_context(
    lead: Lead,
    snapshot: OutreachRunContext,
) -> dict[str, object]:
    """
    The context given to the Writer, Reviewer and Improver.

    Built from the saved snapshot, so a later re-check sees
    exactly what the original agents saw.
    """
    context: dict[str, object] = {
        "target_company": lead.company_name,
        "target_role_requested": lead.target_role,
        "potential_pain_point_unverified": lead.pain_point,
        "seller_offering_user_input": snapshot.sender_offering,
    }

    if snapshot.seller_company is not None:
        # Signature details stay out of the AI's input.
        context["seller_company"] = snapshot.seller_company.model_dump(
            exclude_none=True,
            exclude=SENDER_FIELDS,
        )
        context["call_to_action_style"] = (
            snapshot.seller_company.cta_type or "call"
        )

    if snapshot.selected_product is not None:
        context["selected_product"] = snapshot.selected_product.model_dump(
            exclude_none=True,
        )
        context["product_selection_notice"] = (
            "This product was selected for outreach. "
            "Its suitability for the target company's "
            "actual needs has not been independently "
            "established."
        )

    # Only the name goes to the agents. The reported job title stays
    # in the saved snapshot for you, but the writer must never use it
    # and the reviewer kept flagging it even when the email omitted it.
    if snapshot.selected_contact is not None:
        context["selected_contact"] = {
            "name": snapshot.selected_contact.name,
            "backend_verification_status": (
                snapshot.selected_contact.backend_verification_status
            ),
        }
        context["contact_safety_notice"] = (
            "The contact was manually selected by the "
            "user. Their current employment has not been "
            "independently verified. Use the name only "
            "for the greeting. Do not mention or imply "
            "their job title, role or employer status. "
            "Never invent an email address."
        )

    return context


def prepare_outreach_run(
    db: Session,
    lead: Lead,
    request: OutreachRunRequest,
) -> PreparedRun:
    """
    Build the agent context from the database, never from
    browser-supplied product or company descriptions.
    """
    company_info = (
        f"Company: {lead.company_name}\n"
        f"Website: {lead.website or 'Not provided'}\n"
        f"Industry: {lead.industry}\n"
        f"Target Role: {lead.target_role}\n"
        f"Potential Pain Point: {lead.pain_point}\n"
        "Research the target company using public sources. "
        "Treat potential pain points as unverified."
    )

    snapshot = OutreachRunContext(sender_offering=request.sender_offering)

    if request.seller_company_id is not None:
        seller = get_owned(
            db, Company, lead.organization_id, request.seller_company_id
        )

        if seller is None:
            raise OutreachRequestError(404, "Seller company not found")

        snapshot.seller_company = seller_snapshot(seller)

    if request.selected_product_id is not None:
        product = db.get(CompanyProduct, request.selected_product_id)

        if product is None:
            raise OutreachRequestError(404, "Selected product not found")

        if product.company_id != request.seller_company_id:
            raise OutreachRequestError(
                400,
                "Selected product does not belong "
                "to the selected seller company",
            )

        snapshot.selected_product = product_snapshot(product)

    if request.selected_contact is not None:
        contact = request.selected_contact
        snapshot.selected_contact = RunContactSnapshot(
            name=contact.name,
            reported_job_title=contact.job_title,
            source_url=contact.source_url,
            client_evidence_status=contact.evidence_status,
            backend_verification_status="NOT_VERIFIED",
        )

    return PreparedRun(
        company_info=company_info,
        outreach_context=build_agent_context(lead, snapshot),
        snapshot=snapshot,
        signature=build_signature(snapshot.seller_company),
    )


def snapshot_for_recheck(db: Session, run: OutreachRun) -> OutreachRunContext:
    """
    The saved snapshot, with details filled from the database
    for runs that stored only ids and names.
    """
    if run.context is None:
        return OutreachRunContext(sender_offering=OFFERING_NOT_RECORDED)

    snapshot = OutreachRunContext.model_validate(run.context)

    seller = snapshot.seller_company
    if seller is not None and seller.description is None:
        current = get_owned(db, Company, run.organization_id, seller.id)
        if current is not None:
            snapshot.seller_company = seller_snapshot(current)

    product = snapshot.selected_product
    if product is not None and product.description is None:
        current = db.get(CompanyProduct, product.id)
        owner = (
            get_owned(db, Company, run.organization_id, current.company_id)
            if current is not None
            else None
        )
        if current is not None and owner is not None:
            snapshot.selected_product = product_snapshot(current)

    return snapshot


def save_outreach_run(
    db: Session,
    lead: Lead,
    result: OutreachResult,
    context: OutreachRunContext | None = None,
) -> OutreachRun:
    previous = db.scalar(
        select(func.max(OutreachRun.lead_run_number)).where(
            OutreachRun.lead_id == lead.id,
        )
    )

    run = OutreachRun(
        organization_id=lead.organization_id,
        lead_id=lead.id,
        lead_run_number=(previous or 0) + 1,
        research=result.research.model_dump(mode="json"),
        email=result.email.model_dump(mode="json"),
        review=result.review.model_dump(mode="json"),
        context=context.model_dump(mode="json") if context else None,
        approved=result.approved,
        improved=result.improved,
        improvement_count=result.improvement_count,
        requires_human_review=result.requires_human_review,
        trace_id=result.trace_id,
        llm_requests=result.llm_requests,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost_usd=Decimal(str(UsageTotals(
            requests=result.llm_requests,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        ).estimated_cost_usd)),
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


def record_usage(run: OutreachRun, usage: UsageTotals) -> None:
    """Add the tokens of a later agent call (an edit check) to the run."""
    run.llm_requests += usage.requests
    run.input_tokens += usage.input_tokens
    run.output_tokens += usage.output_tokens
    run.estimated_cost_usd += Decimal(str(usage.estimated_cost_usd))


def get_outreach_run(
    db: Session,
    organization_id: int,
    run_id: int,
) -> OutreachRun | None:
    return get_owned(db, OutreachRun, organization_id, run_id)


def list_outreach_runs(
    db: Session,
    organization_id: int,
    lead_id: int | None = None,
    limit: int = 100,
) -> list[OutreachRun]:
    """Newest first; all of the organisation's leads when lead_id is None."""
    statement = select(OutreachRun).where(
        OutreachRun.organization_id == organization_id
    )

    if lead_id is not None:
        statement = statement.where(OutreachRun.lead_id == lead_id)

    statement = statement.order_by(
        OutreachRun.created_at.desc(),
        OutreachRun.id.desc(),
    ).limit(limit)

    return list(db.scalars(statement).all())


def update_draft(
    db: Session,
    organization_id: int,
    run_id: int,
    email: EmailDraft,
) -> OutreachRun | None:
    run = get_outreach_run(db, organization_id, run_id)

    if run is None:
        return None

    # Any edit invalidates a previous approval and a previous
    # AI check of the edits.
    run.final_email = email.model_dump(mode="json")
    run.final_review = None
    run.human_approved = False
    run.review_override = False
    run.approved_at = None
    run.requires_human_review = True

    db.commit()
    db.refresh(run)
    return run


async def recheck_draft(
    db: Session,
    organization_id: int,
    run_id: int,
) -> OutreachRun | None:
    """
    Ask the Reviewer to check the human-edited draft against
    the evidence saved with the run. Never rewrites the email.
    """
    run = get_outreach_run(db, organization_id, run_id)

    if run is None:
        return None

    if run.final_email is None:
        raise NothingToRecheck

    lead = db.get(Lead, run.lead_id)
    snapshot = snapshot_for_recheck(db, run)

    usage = UsageTotals()
    trace_id = gen_trace_id()

    with trace(
        "Check human edits",
        trace_id=trace_id,
        # Shown together with the trace that generated the draft.
        group_id=run.trace_id or trace_id,
        metadata=trace_metadata(
            run_id=run.id,
            lead_id=run.lead_id,
            organization_id=run.organization_id,
        ),
    ):
        review = await review_email(
            draft=EmailDraft.model_validate(run.final_email),
            research=ResearchReport.model_validate(run.research),
            sender_offering=snapshot.sender_offering,
            context=build_agent_context(lead, snapshot),
            usage=usage,
        )

    run.final_review = review.model_dump(mode="json")
    run.recheck_trace_id = trace_id
    record_usage(run, usage)

    db.commit()
    db.refresh(run)
    return run


def approve_draft(
    db: Session,
    organization_id: int,
    run_id: int,
    acknowledge_failed_review: bool = False,
) -> OutreachRun | None:
    run = get_outreach_run(db, organization_id, run_id)

    if run is None:
        return None

    # Uses the check of the human's edits when there is one.
    passed = latest_review_passed(run.approved, run.final_email, run.final_review)

    # A draft whose latest review failed needs an explicit override.
    if not passed and not acknowledge_failed_review:
        raise FailedReviewNotAcknowledged

    run.human_approved = True
    run.review_override = not passed
    run.approved_at = datetime.now(UTC)
    run.requires_human_review = False

    db.commit()
    db.refresh(run)
    return run
