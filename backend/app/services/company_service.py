
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_product import CompanyProduct
from app.schemas.company import CompanyCreate, ProductCreate


def create_company(
    db: Session,
    data: CompanyCreate,
) -> Company:
    company = Company(**data.model_dump())

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


def list_companies(db: Session) -> list[Company]:
    statement = select(Company).order_by(Company.id.desc())
    return list(db.scalars(statement).all())


def get_company(
    db: Session,
    company_id: int,
) -> Company | None:
    return db.get(Company, company_id)


def update_company(
    db: Session,
    company_id: int,
    data: CompanyCreate,
) -> Company | None:
    company = db.get(Company, company_id)

    if company is None:
        return None

    for field, value in data.model_dump().items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

    return company


def create_product(
    db: Session,
    company_id: int,
    data: ProductCreate,
) -> CompanyProduct:
    product = CompanyProduct(
        company_id=company_id,
        **data.model_dump(),
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def list_products(
    db: Session,
    company_id: int,
) -> list[CompanyProduct]:
    statement = (
        select(CompanyProduct)
        .where(CompanyProduct.company_id == company_id)
        .order_by(CompanyProduct.id.desc())
    )

    return list(db.scalars(statement).all())


def get_product(
    db: Session,
    product_id: int,
) -> CompanyProduct | None:
    return db.get(CompanyProduct, product_id)


def update_product(
    db: Session,
    company_id: int,
    product_id: int,
    data: ProductCreate,
) -> CompanyProduct | None:
    product = db.get(CompanyProduct, product_id)

    if product is None or product.company_id != company_id:
        return None

    for field, value in data.model_dump().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


def delete_product(
    db: Session,
    company_id: int,
    product_id: int,
) -> bool:
    product = db.get(CompanyProduct, product_id)

    if product is None or product.company_id != company_id:
        return False

    db.delete(product)
    db.commit()
    return True
