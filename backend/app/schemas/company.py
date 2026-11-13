
from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    industry: str = Field(min_length=1)
    description: str = Field(min_length=1)
    target_customers: str = Field(min_length=1)
    differentiators: str = Field(min_length=1)


class CompanyResponse(CompanyCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    features: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)


class ProductResponse(ProductCreate):
    id: int
    company_id: int

    model_config = ConfigDict(from_attributes=True)
