from agents import Agent, WebSearchTool
from pydantic import BaseModel, Field


class ResearchFinding(BaseModel):
    claim: str = Field(description="A factual claim about the company")
    source_url: str = Field(description="URL supporting the claim")


class ResearchReport(BaseModel):
    company_name: str
    industry: str

    verified_findings: list[ResearchFinding]

    potential_pain_points: list[str]

    suggested_solution: str
    personalization_angle: str


research_agent = Agent(
    name="Company Research Agent",
    model="gpt-4.1-mini",
    instructions="""
    You are a professional B2B company research analyst.

    Research the company using public web sources.

    Requirements:
    1. Search the web for company information.
    2. Identify factual company information.
    3. Provide a supporting source URL for each
       verified finding.
    4. Separate verified findings from potential
       business challenges.
    5. Never invent company facts, URLs or statistics.
    6. If evidence is unavailable, do not present
       the claim as verified.
    7. Suggest a relevant outreach opportunity.

    Keep the report concise and evidence-based.
    """,
    tools=[WebSearchTool()],
    output_type=ResearchReport,
)
