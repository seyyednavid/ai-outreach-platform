
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OutreachRun(Base):
    __tablename__ = "outreach_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id"),
        index=True,
    )

    research: Mapped[dict] = mapped_column(JSON)
    email: Mapped[dict] = mapped_column(JSON)
    
    final_email: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    human_approved: Mapped[bool] = mapped_column(
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
