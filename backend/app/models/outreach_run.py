
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OutreachRun(Base):
    __tablename__ = "outreach_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Every record belongs to one organisation; queries always filter by it.
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )

    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id"),
        index=True,
    )

    # Run 1, 2, 3 ... within this lead. `id` stays the global number.
    lead_run_number: Mapped[int]

    research: Mapped[dict] = mapped_column(JSON)
    email: Mapped[dict] = mapped_column(JSON)

    final_email: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # AI review of the human-edited draft. Cleared on every edit,
    # so it always describes the current final_email.
    final_review: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Snapshot of the seller, product and contact used for this run,
    # so older runs remain explainable. Null for runs created before
    # this column existed.
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    human_approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # True when a human approved a draft whose final AI review failed.
    review_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    review: Mapped[dict] = mapped_column(JSON)

    approved: Mapped[bool]
    improved: Mapped[bool]
    improvement_count: Mapped[int]
    requires_human_review: Mapped[bool]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
