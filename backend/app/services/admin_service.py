"""Usage and AI quality across all customers, for the product owner only."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.outreach_run import OutreachRun
from app.models.user import User
from app.schemas.admin import (
    OrganizationUsage,
    OwnerOverview,
    QualityStats,
    RunUsage,
    UsageOverview,
)
from app.workflows.outreach_workflow import latest_review_passed


def usage_overview(db: Session) -> UsageOverview:
    totals = (
        select(
            OutreachRun.organization_id,
            func.count(OutreachRun.id).label("drafts"),
            func.sum(case((OutreachRun.human_approved, 1), else_=0)).label("approved"),
            func.sum(OutreachRun.llm_requests).label("requests"),
            func.sum(OutreachRun.input_tokens).label("input_tokens"),
            func.sum(OutreachRun.output_tokens).label("output_tokens"),
            func.sum(OutreachRun.estimated_cost_usd).label("cost"),
            func.max(OutreachRun.created_at).label("last_draft_at"),
        )
        .group_by(OutreachRun.organization_id)
        .subquery()
    )

    rows = db.execute(
        select(Organization, totals)
        .outerjoin(totals, totals.c.organization_id == Organization.id)
        .order_by(func.coalesce(totals.c.cost, 0).desc(), Organization.id)
    ).all()

    emails: dict[int, list[str]] = {}
    for organization_id, email in db.execute(
        select(User.organization_id, User.email).order_by(User.created_at)
    ):
        if email:
            emails.setdefault(organization_id, []).append(email)

    organizations = [
        OrganizationUsage(
            organization_id=row.Organization.id,
            name=row.Organization.name,
            user_emails=emails.get(row.Organization.id, []),
            drafts=row.drafts or 0,
            approved_drafts=row.approved or 0,
            llm_requests=row.requests or 0,
            input_tokens=row.input_tokens or 0,
            output_tokens=row.output_tokens or 0,
            estimated_cost_usd=round(float(row.cost or 0), 6),
            last_draft_at=row.last_draft_at,
        )
        for row in rows
    ]

    return UsageOverview(
        organizations=organizations,
        total_drafts=sum(org.drafts for org in organizations),
        total_tokens=sum(org.input_tokens + org.output_tokens for org in organizations),
        total_estimated_cost_usd=round(
            sum(org.estimated_cost_usd for org in organizations), 6
        ),
    )


def _flags(review: dict | None) -> list[str]:
    if not isinstance(review, dict):
        return []
    return [flag for flag in review.get("unsupported_claims") or [] if isinstance(flag, str)]


def _score(review: dict | None) -> float | None:
    if not isinstance(review, dict):
        return None
    score = review.get("overall_score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return float(score)
    return None


def quality_stats(runs: list[OutreachRun]) -> QualityStats:
    """Counted in Python: the reviews are JSON, and an MVP has few runs."""
    scores = [score for run in runs if (score := _score(run.review)) is not None]
    final_flags = [
        _flags(run.final_review if run.final_review is not None else run.review)
        for run in runs
    ]
    every_flag = [flag for flags in final_flags for flag in flags]

    return QualityStats(
        drafts=len(runs),
        ai_passed=sum(run.approved for run in runs),
        first_try_passed=sum(run.approved and run.improvement_count == 0 for run in runs),
        average_score=round(sum(scores) / len(scores), 2) if scores else None,
        average_rewrites=(
            round(sum(run.improvement_count for run in runs) / len(runs), 2) if runs else None
        ),
        edited_by_human=sum(run.final_email is not None for run in runs),
        edits_checked_by_ai=sum(run.final_review is not None for run in runs),
        edits_failed_check=sum(
            run.final_review is not None
            and not latest_review_passed(run.approved, run.final_email, run.final_review)
            for run in runs
        ),
        human_approved=sum(run.human_approved for run in runs),
        overrides=sum(run.review_override for run in runs),
        flags_kept=len(every_flag),
        flags_ignored_by_code=sum(
            len((run.review or {}).get("ignored_claims") or [])
            + len((run.final_review or {}).get("ignored_claims") or [])
            for run in runs
        ),
        placeholder_flags=sum("Unfilled placeholder" in flag for flag in every_flag),
        missing_signature_flags=sum(flag.startswith('"(no signature)"') for flag in every_flag),
    )


def owner_overview(db: Session) -> OwnerOverview:
    runs = list(db.scalars(select(OutreachRun)).all())
    week_ago = datetime.now(UTC) - timedelta(days=7)
    cost = sum(float(run.estimated_cost_usd or 0) for run in runs)

    return OwnerOverview(
        customers=db.scalar(select(func.count(Organization.id))) or 0,
        users=db.scalar(select(func.count(User.id))) or 0,
        drafts=len(runs),
        drafts_last_7_days=sum(run.created_at >= week_ago for run in runs),
        total_tokens=sum(run.input_tokens + run.output_tokens for run in runs),
        estimated_cost_usd=round(cost, 6),
        # Only runs that recorded usage (newer than tracing) count here.
        average_cost_per_draft_usd=(
            round(cost / tracked, 6)
            if (tracked := sum(run.llm_requests > 0 for run in runs))
            else None
        ),
        quality=quality_stats(runs),
    )


def recent_runs(
    db: Session,
    organization_id: int | None = None,
    limit: int = 50,
) -> list[RunUsage]:
    statement = (
        select(OutreachRun, Organization.name)
        .join(Organization, Organization.id == OutreachRun.organization_id)
        .order_by(OutreachRun.created_at.desc(), OutreachRun.id.desc())
        .limit(limit)
    )
    if organization_id is not None:
        statement = statement.where(OutreachRun.organization_id == organization_id)

    results = []
    for run, organization_name in db.execute(statement).all():
        latest = run.final_review if run.final_review is not None else run.review
        results.append(
            RunUsage.model_validate(run).model_copy(
                update={
                    "organization_name": organization_name,
                    "overall_score": _score(latest),
                }
            )
        )
    return results
