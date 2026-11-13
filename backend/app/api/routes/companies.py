
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
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

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    data: CompanyCreate,
    db: DbSession,
):
    return company_service.create_company(db, data)


@router.get(
    "",
    response_model=list[CompanyResponse],
)
def list_companies(db: DbSession):
    return company_service.list_companies(db)


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
)
def get_company(
    company_id: int,
    db: DbSession,
):
    company = company_service.get_company(db, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return company


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
)
def update_company(
    company_id: int,
    data: CompanyCreate,
    db: DbSession,
):
    company = company_service.update_company(
        db,
        company_id,
        data,
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

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
):
    company = company_service.get_company(db, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    try:
        return company_service.create_product(
            db,
            company_id,
            data,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A product with this name already exists for this company",
        ) from exc



@router.get(
    "/{company_id}/products",
    response_model=list[ProductResponse],
)
def list_products(
    company_id: int,
    db: DbSession,
):
    company = company_service.get_company(db, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return company_service.list_products(db, company_id)



@router.put(
    "/{company_id}/products/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    company_id: int,
    product_id: int,
    data: ProductCreate,
    db: DbSession,
):
    try:
        product = company_service.update_product(
            db,
            company_id,
            product_id,
            data,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A product with this name already exists for this company",
        ) from exc

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
):
    deleted = company_service.delete_product(
        db,
        company_id,
        product_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Product not found for this company",
        )
