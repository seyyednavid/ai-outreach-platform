import json
from typing import Annotated

from agents import Runner
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.contact_discovery_agent import contact_discovery_agent
from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.contact_discovery import (
    ContactDiscoveryRequest,
    ContactDiscoveryResponse,
    ContactDiscoveryResult,
    ReviewedContact,
)
from app.services.contact_quality import clean_and_rank_contacts
from app.services.source_verification import verify_contact_source

router = APIRouter(
    prefix="/contacts",
    tags=["Contact Discovery"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/discover",
    response_model=ContactDiscoveryResponse,
)
async def discover_contacts(
    request: ContactDiscoveryRequest,
    db: DbSession,
):
    # Step 1: Get the target lead from PostgreSQL.
    lead = db.get(Lead, request.lead_id)

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    # Step 2: Prepare the context for the AI agent.
    research_context = {
        "target_company": lead.company_name,
        "website": lead.website,
        "industry": lead.industry,
        "preferred_contact_role": lead.target_role,
        "potential_business_need_unverified": lead.pain_point,
        "task": (
            "Find up to five publicly documented business "
            "contacts relevant to this company's operations. "
            "Provide supporting public sources. Do not invent "
            "people, roles, or email addresses."
        ),
    }

    # Step 3: Run the Contact Discovery Agent.
    result = await Runner.run(
        contact_discovery_agent,
        input=json.dumps(
            research_context,
            ensure_ascii=False,
        ),
    )

    discovery: ContactDiscoveryResult = result.final_output

    # Step 4: Validate, deduplicate and rank contacts in Python.
    reviewed = clean_and_rank_contacts(
        discovery.contacts,
        target_company=lead.company_name,
    )

    # Step 5: Add Python-calculated quality information.
    contacts = [
        ReviewedContact(
            **contact.model_dump(),
            relevance_score=score,
            evidence_status=evidence_status,
            evidence_warnings=warnings,
        )
        for contact, score, evidence_status, warnings in reviewed
    ]

    verified_contacts = []

    for contact in contacts:
        verified_contact = await verify_contact_source(contact)
        verified_contacts.append(verified_contact)

    # Step 6: Return the final API response.
    return ContactDiscoveryResponse(
        lead_id=lead.id,
        target_company=lead.company_name,
        contacts=verified_contacts,
        search_summary=discovery.search_summary,
        limitations=discovery.limitations,
    )
