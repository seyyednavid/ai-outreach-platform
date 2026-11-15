from fastapi import APIRouter, HTTPException

from app.api.deps import AuthUser, DbSession
from app.schemas.outreach import (
    OutreachApprovalRequest,
    OutreachDraftUpdate,
    OutreachRunRequest,
    OutreachRunResponse,
)
from app.services import lead_service, outreach_service
from app.services.outreach_service import (
    FailedReviewNotAcknowledged,
    NothingToRecheck,
    OutreachRequestError,
)
from app.workflows.outreach_workflow import run_outreach

router = APIRouter(prefix="/outreach", tags=["Outreach"])


def run_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Run not found")


@router.post("/run", response_model=OutreachRunResponse)
async def run_outreach_for_lead(
    request: OutreachRunRequest,
    db: DbSession,
    user: AuthUser,
):
    lead = lead_service.get_lead(db, user.organization_id, request.lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    try:
        prepared = outreach_service.prepare_outreach_run(db, lead, request)
    except OutreachRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc

    result = await run_outreach(
        company_info=prepared.company_info,
        sender_offering=request.sender_offering,
        outreach_context=prepared.outreach_context,
        signature=prepared.signature,
        metadata={
            "organization_id": user.organization_id,
            "lead_id": lead.id,
            "seller_company_id": request.seller_company_id,
            "product_selected": request.selected_product_id is not None,
            "contact_selected": request.selected_contact is not None,
        },
    )
    result = outreach_service.flag_missing_signature(result, prepared.signature)

    return outreach_service.save_outreach_run(
        db=db,
        lead=lead,
        result=result,
        context=prepared.snapshot,
    )


@router.get(
    "/runs",
    response_model=list[OutreachRunResponse],
)
def list_recent_runs(db: DbSession, user: AuthUser):
    """The 100 newest runs across all leads, for the Drafts page."""
    return outreach_service.list_outreach_runs(db, user.organization_id)


@router.get(
    "/runs/{run_id}",
    response_model=OutreachRunResponse,
)
def get_run(
    run_id: int,
    db: DbSession,
    user: AuthUser,
):
    run = outreach_service.get_outreach_run(db, user.organization_id, run_id)

    if run is None:
        raise run_not_found()

    return run


@router.get(
    "/leads/{lead_id}/runs",
    response_model=list[OutreachRunResponse],
)
def get_lead_runs(
    lead_id: int,
    db: DbSession,
    user: AuthUser,
):
    lead = lead_service.get_lead(db, user.organization_id, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return outreach_service.list_outreach_runs(
        db,
        user.organization_id,
        lead.id,
    )


@router.put(
    "/runs/{run_id}/draft",
    response_model=OutreachRunResponse,
)
def update_outreach_draft(
    run_id: int,
    request: OutreachDraftUpdate,
    db: DbSession,
    user: AuthUser,
):
    run = outreach_service.update_draft(
        db=db,
        organization_id=user.organization_id,
        run_id=run_id,
        email=request.email,
    )

    if run is None:
        raise run_not_found()

    return run


@router.post(
    "/runs/{run_id}/review",
    response_model=OutreachRunResponse,
)
async def recheck_outreach_draft(
    run_id: int,
    db: DbSession,
    user: AuthUser,
):
    """Run the AI reviewer on the human-edited draft."""
    try:
        run = await outreach_service.recheck_draft(
            db=db,
            organization_id=user.organization_id,
            run_id=run_id,
        )
    except NothingToRecheck as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Edit and save the email first. The AI has "
                "already reviewed its own draft."
            ),
        ) from exc

    if run is None:
        raise run_not_found()

    return run


@router.post(
    "/runs/{run_id}/approve",
    response_model=OutreachRunResponse,
)
def approve_outreach_draft(
    run_id: int,
    db: DbSession,
    user: AuthUser,
    request: OutreachApprovalRequest | None = None,
):
    acknowledge = request.acknowledge_failed_review if request else False

    try:
        run = outreach_service.approve_draft(
            db=db,
            organization_id=user.organization_id,
            run_id=run_id,
            acknowledge_failed_review=acknowledge,
        )
    except FailedReviewNotAcknowledged as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "This draft's latest AI review failed. Confirm you "
                "have checked the flagged issues to approve it anyway."
            ),
        ) from exc

    if run is None:
        raise run_not_found()

    return run
