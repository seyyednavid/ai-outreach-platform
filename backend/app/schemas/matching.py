
from typing import Literal

from pydantic import BaseModel, Field


class SolutionMatchRequest(BaseModel):
    company_id: int = Field(gt=0)
    lead_id: int = Field(gt=0)


class SolutionMatchResult(BaseModel):
    recommended_product_id: int | None = None
    potential_use_case: str
    reasoning: str
    confidence: Literal["low", "medium", "high"]
    customer_need_verified: bool
    missing_information: list[str]


class SolutionMatchResponse(BaseModel):
    company_id: int
    lead_id: int
    recommended_product_id: int | None
    recommended_product_name: str | None
    potential_use_case: str
    reasoning: str
    confidence: Literal["low", "medium", "high"]
    customer_need_verified: bool
    missing_information: list[str]
