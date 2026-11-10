
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.outreach_run import OutreachRun
from app.schemas.dashboard import DashboardStats


def get_dashboard_stats(db: Session) -> DashboardStats:
    """Calculate dashboard statistics from PostgreSQL."""

    total_leads = db.scalar(
        select(func.count(Lead.id))
    ) or 0

    total_runs = db.scalar(
        select(func.count(OutreachRun.id))
    ) or 0

    human_approved = db.scalar(
        select(func.count(OutreachRun.id)).where(
            OutreachRun.human_approved.is_(True)
        )
    ) or 0

    # Review scores are stored inside the JSON review column.
    review_scores = db.scalars(
        select(OutreachRun.review)
    ).all()

    scores = [
        float(review["overall_score"])
        for review in review_scores
        if isinstance(review, dict)
        and isinstance(review.get("overall_score"), (int, float))
        and not isinstance(review.get("overall_score"), bool)
    ]

    average_score = (
        round(sum(scores) / len(scores), 2)
        if scores
        else 0.0
    )

    return DashboardStats(
        total_leads=total_leads,
        total_outreach_runs=total_runs,
        human_approved_emails=human_approved,
        average_review_score=average_score,
    )
