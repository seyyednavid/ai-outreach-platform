
import json
from typing import Annotated

from agents import Runner
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.solution_matching_agent import (
    solution_matching_agent,
)
from app.core.database import get_db
from app.models.company import Company
from app.models.company_product import CompanyProduct
from app.models.lead import Lead
from app.schemas.matching import (
    SolutionMatchRequest,
    SolutionMatchResponse,
    SolutionMatchResult,
)

router = APIRouter(
    prefix="/matching",
    tags=["Solution Matching"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/preview",
    response_model=SolutionMatchResponse,
)
async def preview_solution_match(
    request: SolutionMatchRequest,
    db: DbSession,
):
    company = db.get(Company, request.company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Seller company not found",
        )

    lead = db.get(Lead, request.lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Target lead not found",
        )

    products = list(
        db.scalars(
            select(CompanyProduct).where(
                CompanyProduct.company_id == company.id
            )
        ).all()
    )

    if not products:
        raise HTTPException(
            status_code=400,
            detail="Add products to the seller company first",
        )

    company_context = {
        "seller": {
            "name": company.name,
            "industry": company.industry,
            "description": company.description,
            "target_customers": company.target_customers,
            "differentiators": company.differentiators,
        },
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "features": product.features,
                "use_cases": product.use_cases,
            }
            for product in products
        ],
        "target_company": {
            "name": lead.company_name,
            "website": lead.website,
            "industry": lead.industry,
            "target_role": lead.target_role,
            "potential_pain_point_unverified": lead.pain_point,
        },
    }

    result = await Runner.run(
        solution_matching_agent,
        input=json.dumps(company_context, ensure_ascii=False),
    )

    match: SolutionMatchResult = result.final_output

    # Never trust an LLM-generated database ID without checking it.
    product_by_id = {
        product.id: product for product in products
    }

    product = product_by_id.get(match.recommended_product_id)

    if match.recommended_product_id is not None and product is None:
        raise HTTPException(
            status_code=502,
            detail="AI selected a product outside the catalog",
        )

    # This preview uses unverified lead information only.
    return SolutionMatchResponse(
        company_id=company.id,
        lead_id=lead.id,
        recommended_product_id=product.id if product else None,
        recommended_product_name=product.name if product else None,
        potential_use_case=match.potential_use_case,
        reasoning=match.reasoning,
        confidence=match.confidence,
        customer_need_verified=False,
        missing_information=match.missing_information,
    )
