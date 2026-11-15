from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_product import CompanyProduct
from app.schemas.company import CompanyCreate, ProductCreate
from app.services.ownership import get_owned


def create_company(
    db: Session,
    organization_id: int,
    data: CompanyCreate,
) -> Company:
    company = Company(organization_id=organization_id, **data.model_dump())

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


def list_companies(db: Session, organization_id: int) -> list[Company]:
    statement = (
        select(Company)
        .where(Company.organization_id == organization_id)
        .order_by(Company.id.desc())
    )
    return list(db.scalars(statement).all())


def get_company(
    db: Session,
    organization_id: int,
    company_id: int,
) -> Company | None:
    return get_owned(db, Company, organization_id, company_id)


def update_company(
    db: Session,
    organization_id: int,
    company_id: int,
    data: CompanyCreate,
) -> Company | None:
    company = get_company(db, organization_id, company_id)

    if company is None:
        return None

    for field, value in data.model_dump().items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

    return company


# Product functions take a company that the caller has already
# checked with get_company, so they never cross organisations.


def create_product(
    db: Session,
    company: Company,
    data: ProductCreate,
) -> CompanyProduct:
    product = CompanyProduct(
        company_id=company.id,
        **data.model_dump(),
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def list_products(
    db: Session,
    company: Company,
) -> list[CompanyProduct]:
    statement = (
        select(CompanyProduct)
        .where(CompanyProduct.company_id == company.id)
        .order_by(CompanyProduct.id.desc())
    )

    return list(db.scalars(statement).all())


def get_product(
    db: Session,
    company: Company,
    product_id: int,
) -> CompanyProduct | None:
    product = db.get(CompanyProduct, product_id)

    if product is None or product.company_id != company.id:
        return None

    return product


def update_product(
    db: Session,
    company: Company,
    product_id: int,
    data: ProductCreate,
) -> CompanyProduct | None:
    product = get_product(db, company, product_id)

    if product is None:
        return None

    for field, value in data.model_dump().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


def delete_product(
    db: Session,
    company: Company,
    product_id: int,
) -> bool:
    product = get_product(db, company, product_id)

    if product is None:
        return False

    db.delete(product)
    db.commit()
    return True
