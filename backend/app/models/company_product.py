from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompanyProduct(Base):
    __tablename__ = "company_products"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_company_product_name",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        index=True,
    )

    name: Mapped[str]
    description: Mapped[str]

    features: Mapped[list[str]] = mapped_column(JSON)
    use_cases: Mapped[list[str]] = mapped_column(JSON)
