from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthUser, DbSession
from app.models.company import Company
from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    ProductCreate,
    ProductResponse,
)
from app.services import company_service

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

DUPLICATE_PRODUCT = "A product with this name already exists for this company"


def owned_company(db: DbSession, user: AuthUser, company_id: int) -> Company:
    company = company_service.get_company(db, user.organization_id, company_id)

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    data: CompanyCreate,
    db: DbSession,
    user: AuthUser,
):
    return company_service.create_company(db, user.organization_id, data)


@router.get(
    "",
    response_model=list[CompanyResponse],
)
def list_companies(db: DbSession, user: AuthUser):
    return company_service.list_companies(db, user.organization_id)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
)
def get_company(
    company_id: int,
    db: DbSession,
    user: AuthUser,
):
    return owned_company(db, user, company_id)


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
)
def update_company(
    company_id: int,
    data: CompanyCreate,
    db: DbSession,
    user: AuthUser,
):
    company = company_service.update_company(
        db,
        user.organization_id,
        company_id,
        data,
    )

    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@router.post(
    "/{company_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    company_id: int,
    data: ProductCreate,
    db: DbSession,
    user: AuthUser,
):
    company = owned_company(db, user, company_id)

    try:
        return company_service.create_product(db, company, data)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_PRODUCT) from exc


@router.get(
    "/{company_id}/products",
    response_model=list[ProductResponse],
)
def list_products(
    company_id: int,
    db: DbSession,
    user: AuthUser,
):
    company = owned_company(db, user, company_id)
    return company_service.list_products(db, company)


@router.put(
    "/{company_id}/products/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    company_id: int,
    product_id: int,
    data: ProductCreate,
    db: DbSession,
    user: AuthUser,
):
    company = owned_company(db, user, company_id)

    try:
        product = company_service.update_product(db, company, product_id, data)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_PRODUCT) from exc

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found for this company",
        )

    return product


@router.delete(
    "/{company_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product(
    company_id: int,
    product_id: int,
    db: DbSession,
    user: AuthUser,
):
    company = owned_company(db, user, company_id)

    if not company_service.delete_product(db, company, product_id):
        raise HTTPException(
            status_code=404,
            detail="Product not found for this company",
        )
