
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]
    website: Mapped[str | None]
    industry: Mapped[str]

    description: Mapped[str]
    target_customers: Mapped[str]
    differentiators: Mapped[str]

    # Who signs the emails. The signature is added by code, never by the AI.
    sender_name: Mapped[str | None] = mapped_column(String(200))
    sender_job_title: Mapped[str | None] = mapped_column(String(200))
    sign_off: Mapped[str | None] = mapped_column(String(100))
    sender_email: Mapped[str | None] = mapped_column(String(320))
    sender_phone: Mapped[str | None] = mapped_column(String(50))

    # How every email asks the recipient to respond: "call" or "email".
    cta_type: Mapped[str] = mapped_column(
        String(20),
        default="call",
        server_default="call",
    )
