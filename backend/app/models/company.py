
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
