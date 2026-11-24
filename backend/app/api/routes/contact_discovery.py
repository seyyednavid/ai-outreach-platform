import asyncio
import json
import logging

from agents import Runner, trace
from fastapi import APIRouter, HTTPException

from app.agents.contact_discovery_agent import contact_discovery_agent
from app.api.deps import AuthUser, DbSession
from app.core.logging_config import describe_exception
from app.core.tracing import run_config, trace_metadata
from app.models.lead import Lead
from app.schemas.contact_discovery import (
    ContactDiscoveryRequest,
    ContactDiscoveryResponse,
    ContactDiscoveryResult,
    ReviewedContact,
)
from app.services.contact_quality import clean_and_rank_contacts
from app.services.ownership import get_owned
from app.services.source_verification import site_domain, verify_contact_source

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/contacts",
    tags=["Contact Discovery"],
)

# One search per kind of source, run in parallel. A single run
# usually stops after one web search (seen in the traces), so
# breadth is guaranteed by code rather than by the prompt.
SEARCH_FOCUSES = (
    (
        "The company's own leadership, management or 'our people' pages, "
        "and the leadership pages or annual report of its parent company or group."
    ),
    (
        "Press releases and company news announcing appointments to "
        "operations, retail or customer experience leadership roles."
    ),
    (
        "Trade press and industry news, such as interviews and appointment "
        "news, that name the company's operations or retail leaders."
    ),
)

MAX_CONTACTS = 5


@router.post(
    "/discover",
    response_model=ContactDiscoveryResponse,
)
async def discover_contacts(
    request: ContactDiscoveryRequest,
    db: DbSession,
    user: AuthUser,
):
    # Step 1: Get the target lead from PostgreSQL.
    lead = get_owned(db, Lead, user.organization_id, request.lead_id)

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

    # Step 3: One focused search per kind of source, all in one trace.
    with trace(
        "Contact discovery",
        metadata=trace_metadata(organization_id=user.organization_id, lead_id=lead.id),
    ):
        outcomes = await asyncio.gather(
            *(
                Runner.run(
                    contact_discovery_agent,
                    input=json.dumps(
                        {**research_context, "search_focus": focus},
                        ensure_ascii=False,
                    ),
                    run_config=run_config(),
                )
                for focus in SEARCH_FOCUSES
            ),
            return_exceptions=True,
        )

    discoveries: list[ContactDiscoveryResult] = []
    for outcome in outcomes:
        if isinstance(outcome, BaseException):
            # Type and location only: the message can quote model output.
            logger.warning("A contact search failed: %s", describe_exception(outcome))
        else:
            discoveries.append(outcome.final_output)

    # One failed search is fine; all of them failing is not.
    if not discoveries:
        raise HTTPException(
            status_code=502,
            detail="The contact search failed. Try again in a moment.",
        )

    # Step 4: Validate, deduplicate and rank contacts in Python.
    reviewed = clean_and_rank_contacts(
        [contact for discovery in discoveries for contact in discovery.contacts],
        target_company=lead.company_name,
        target_role=lead.target_role,
    )[:MAX_CONTACTS]

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

    # The lead's own website counts as a checkable source.
    lead_domain = site_domain(lead.website)
    trusted = (lead_domain,) if lead_domain else ()

    verified_contacts = []

    for contact in contacts:
        verified_contact = await verify_contact_source(contact, trusted)
        verified_contacts.append(verified_contact)

    # Step 6: Return the final API response. The summary comes from the
    # search that found the most contacts; limitations from all of them.
    best = max(discoveries, key=lambda discovery: len(discovery.contacts))
    limitations = list(
        dict.fromkeys(item for discovery in discoveries for item in discovery.limitations)
    )

    return ContactDiscoveryResponse(
        lead_id=lead.id,
        target_company=lead.company_name,
        contacts=verified_contacts,
        search_summary=best.search_summary,
        limitations=limitations,
    )
