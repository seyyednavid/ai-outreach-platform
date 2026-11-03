
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str] = mapped_column(String(150))
    target_role: Mapped[str] = mapped_column(String(150))
    pain_point: Mapped[str] = mapped_column(Text)

    recipient_name: Mapped[str | None] = mapped_column(String(200))
    recipient_email: Mapped[str | None] = mapped_column(String(320))
