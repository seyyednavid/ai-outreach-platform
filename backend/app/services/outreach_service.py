
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.writer_agent import EmailDraft
from app.models.outreach_run import OutreachRun
from app.workflows.outreach_workflow import OutreachResult


def save_outreach_run(
    db: Session,
    lead_id: int,
    result: OutreachResult,
) -> OutreachRun:
    run = OutreachRun(
        lead_id=lead_id,
        research=result.research.model_dump(mode="json"),
        email=result.email.model_dump(mode="json"),
        review=result.review.model_dump(mode="json"),
        approved=result.approved,
        improved=result.improved,
        improvement_count=result.improvement_count,
        requires_human_review=result.requires_human_review,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


def get_outreach_run(
    db: Session,
    run_id: int,
) -> OutreachRun | None:
    return db.get(OutreachRun, run_id)


def list_outreach_runs(
    db: Session,
    lead_id: int,
) -> list[OutreachRun]:
    statement = (
        select(OutreachRun)
        .where(OutreachRun.lead_id == lead_id)
        .order_by(OutreachRun.created_at.desc(), OutreachRun.id.desc())
    )

    return list(db.scalars(statement).all())



def update_draft(
    db: Session,
    run_id: int,
    email: EmailDraft,
) -> OutreachRun | None:
    run = db.get(OutreachRun, run_id)

    if run is None:
        return None

    run.final_email = email.model_dump(mode="json")
    run.human_approved = False
    run.approved_at = None
    run.requires_human_review = True

    db.commit()
    db.refresh(run)
    return run


def approve_draft(
    db: Session,
    run_id: int,
) -> OutreachRun | None:
    run = db.get(OutreachRun, run_id)

    if run is None:
        return None

    run.human_approved = True
    run.approved_at = datetime.now(UTC)
    run.requires_human_review = False

    db.commit()
    db.refresh(run)
    return run
