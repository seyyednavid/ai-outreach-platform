"""Usage across all customers, for the product owner only."""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.outreach_run import OutreachRun
from app.models.user import User
from app.schemas.admin import OrganizationUsage, UsageOverview


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


def organization_runs(
    db: Session,
    organization_id: int,
    limit: int = 50,
) -> list[OutreachRun]:
    return list(
        db.scalars(
            select(OutreachRun)
            .where(OutreachRun.organization_id == organization_id)
            .order_by(OutreachRun.created_at.desc(), OutreachRun.id.desc())
            .limit(limit)
        ).all()
    )
