"""
Simulate several customers using the product, with the real agents.

Creates demo customers (organisations named "[Demo] ..."), each with
its own seller company, products, signature and leads, then drives the
same route functions the browser uses: product matching, contact
discovery, draft generation, human edits, AI checks of the edits and
approval. Every agent call is traced and costs real OpenAI credit.

Demo customers cannot sign in (they have no Supabase account); the
owner sees them in the Owner Console.

    uv run python -m scripts.simulate_customers --out results.json
    uv run python -m scripts.simulate_customers --customers 1 --leads 1   # smoke test
    uv run python -m scripts.simulate_customers --cleanup                  # delete demo data
"""

import argparse
import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from agents.tracing import get_trace_provider
from fastapi import HTTPException
from sqlalchemy import delete, select

import app.main  # noqa: F401  (sets the OpenAI key for agents and tracing)
from app.agents.writer_agent import EmailDraft
from app.api.routes.contact_discovery import discover_contacts
from app.api.routes.matching import preview_solution_match
from app.api.routes.outreach import (
    approve_outreach_draft,
    recheck_outreach_draft,
    run_outreach_for_lead,
    update_outreach_draft,
)
from app.core.database import SessionLocal
from app.models import (
    Company,
    CompanyProduct,
    GmailConnection,
    Lead,
    Organization,
    OutreachRun,
    User,
)
from app.schemas.company import CompanyCreate, ProductCreate
from app.schemas.contact_discovery import ContactDiscoveryRequest
from app.schemas.lead import LeadCreate
from app.schemas.matching import SolutionMatchRequest
from app.schemas.outreach import (
    OutreachApprovalRequest,
    OutreachDraftUpdate,
    OutreachRunRequest,
    SelectedContact,
)
from app.services import company_service, lead_service
from app.services.user_service import CurrentUser

DEMO_PREFIX = "[Demo] "

# A claim no evidence supports: the AI check of human edits should flag it.
UNSUPPORTED_CLAIM = (
    "We have already helped more than 200 UK retailers cut waiting times by 40%."
)

# Seller companies and products are invented. Most leads are real public
# companies, so research has something to find; two are fictional, to see
# whether the AI invents facts about a company that does not exist.
CUSTOMERS = [
    {
        "seller": {
            "name": "QueueWise Systems",
            "industry": "Queue management",
            "description": (
                "QueueWise designs queue management for retail and pharmacy "
                "counters: virtual queues and call-forward displays."
            ),
            "target_customers": "UK retailers, pharmacies and service counters",
            "differentiators": "Installed in under a week; works alongside existing tills",
            "sender_name": "Priya Shah",
            "sender_job_title": "Head of Partnerships",
            "sign_off": "Kind regards",
            "sender_email": "priya.shah@example.com",
            "sender_phone": "+44 20 7946 0101",
            "cta_type": "call",
        },
        "products": [
            {
                "name": "Virtual Queue App",
                "description": "Customers join a queue from their phone and get a text when it is their turn.",
                "features": ["Join by QR code", "SMS alerts", "Live wait times"],
                "use_cases": ["Pharmacy prescription collection", "Click and collect desks"],
            },
            {
                "name": "Call-Forward Display",
                "description": "Screens and audio that call the next customer to a free till or counter.",
                "features": ["Audio and visual calls", "Up to 30 tills"],
                "use_cases": ["Checkout queues", "Service counters"],
            },
        ],
        "offering": "Queue management systems that reduce waiting at tills and service counters.",
        "leads": [
            ("Boots", "https://www.boots.com", "Pharmacy and health retail",
             "Head of Store Operations", "Possible queues at pharmacy counters at busy times", False),
            ("Argos", "https://www.argos.co.uk", "Retail",
             "Head of Retail Operations", "Possible waits at collection points", False),
            ("Brindle & Moss Grocers", None, "Grocery retail",
             "Operations Director", "Possible checkout queues at weekends", True),
        ],
    },
    {
        "seller": {
            "name": "ShelfSense Analytics",
            "industry": "Retail analytics",
            "description": (
                "ShelfSense uses small shelf cameras to spot empty shelves and "
                "misplaced products, and alerts store staff."
            ),
            "target_customers": "UK supermarkets and convenience chains",
            "differentiators": "Alerts within minutes; no customer images are stored",
            "sender_name": "Tom Ellis",
            "sender_job_title": "Sales Director",
            "sign_off": "Best regards",
            "sender_email": "tom.ellis@example.com",
            "sender_phone": "+44 20 7946 0202",
            "cta_type": "email",
        },
        "products": [
            {
                "name": "Shelf Gap Alerts",
                "description": "Cameras detect empty shelf space and send an alert to staff handsets.",
                "features": ["Gap detection", "Staff alerts", "Daily availability report"],
                "use_cases": ["Fresh produce", "Promotional aisles"],
            },
            {
                "name": "Planogram Checker",
                "description": "Compares shelves with the planned layout and lists the differences.",
                "features": ["Layout comparison", "Photo evidence"],
                "use_cases": ["New range launches", "Store audits"],
            },
        ],
        "offering": "Shelf monitoring that helps stores keep products available on the shelf.",
        "leads": [
            ("Sainsbury's", "https://www.sainsburys.co.uk", "Grocery retail",
             "Director of Retail Operations", "Possible gaps on shelves at peak times", False),
            ("Co-op", "https://www.coop.co.uk", "Convenience retail",
             "Head of Store Standards", "Possible availability issues in small stores", False),
            ("Lidl GB", "https://www.lidl.co.uk", "Grocery retail",
             "Head of Operations", "Possible delays in refilling shelves", False),
        ],
    },
    {
        "seller": {
            "name": "GreenRoute Delivery",
            "industry": "Last-mile logistics",
            "description": (
                "GreenRoute runs electric van fleets for same-day home delivery "
                "on behalf of retailers."
            ),
            "target_customers": "UK retailers offering home delivery",
            "differentiators": "Fully electric fleet; two-hour delivery windows",
            "sender_name": "Amara Okafor",
            "sender_job_title": "Business Development Manager",
            "sign_off": "Many thanks",
            "sender_email": "amara.okafor@example.com",
            "sender_phone": "+44 20 7946 0303",
            "cta_type": "call",
        },
        "products": [
            {
                "name": "Same-Day EV Delivery",
                "description": "Electric vans deliver orders the same day in two-hour windows.",
                "features": ["Two-hour windows", "Live tracking for customers"],
                "use_cases": ["Online grocery orders", "Urgent home delivery"],
            },
        ],
        "offering": "Electric same-day delivery for retailers' online orders.",
        "leads": [
            ("Iceland Foods", "https://www.iceland.co.uk", "Frozen food retail",
             "Head of Home Delivery", "Possible pressure on delivery capacity", False),
            ("Holland & Barrett", "https://www.hollandandbarrett.com", "Health retail",
             "Head of Ecommerce Operations", "Possible demand for faster delivery", False),
            ("Harrowgate Home & Garden", None, "Home and garden retail",
             "Logistics Manager", "Possible delivery delays for bulky items", True),
        ],
    },
    {
        "seller": {
            "name": "RotaPilot",
            "industry": "Workforce software",
            "description": (
                "RotaPilot is staff scheduling software that plans shifts "
                "around expected footfall."
            ),
            "target_customers": "UK retail and food-to-go chains",
            "differentiators": "Shift swaps in the app; forecasts from till data",
            "sender_name": "Daniel Reyes",
            "sender_job_title": "Account Executive",
            "sign_off": "Best wishes",
            "sender_email": "daniel.reyes@example.com",
            "sender_phone": "+44 20 7946 0404",
            "cta_type": "email",
        },
        "products": [
            {
                "name": "Footfall Rota Planner",
                "description": "Builds weekly rotas from expected footfall and till data.",
                "features": ["Footfall forecasts", "Rota templates"],
                "use_cases": ["Busy lunchtimes", "Seasonal peaks"],
            },
            {
                "name": "Shift Swap App",
                "description": "Staff swap shifts in an app, with manager approval.",
                "features": ["Manager approval", "Push notifications"],
                "use_cases": ["Last-minute absences"],
            },
        ],
        "offering": "Staff scheduling that matches shifts to expected customer demand.",
        "leads": [
            ("Greggs", "https://www.greggs.co.uk", "Food-to-go retail",
             "Head of Retail Operations", "Possible understaffing at lunchtime peaks", False),
            ("Pret A Manger", "https://www.pret.co.uk", "Food-to-go retail",
             "Operations Director", "Possible queues during the morning rush", False),
            ("Superdrug", "https://www.superdrug.com", "Health and beauty retail",
             "Head of Store Operations", "Possible staffing gaps at weekends", False),
        ],
    },
]


@dataclass
class LeadResult:
    customer: str
    lead: str
    fictional: bool
    scenario: str
    run_id: int | None = None
    contacts_found: int | None = None
    contact_used: bool = False
    matched_product: str | None = None
    match_confidence: str | None = None
    score: float | None = None
    passed: bool | None = None
    rewrites: int | None = None
    flags: list[str] = field(default_factory=list)
    ignored_flags: int = 0
    verified_findings: int | None = None
    edit_check_passed: bool | None = None
    edit_check_flags: list[str] = field(default_factory=list)
    human_action: str | None = None
    tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0
    subject: str | None = None
    body: str | None = None
    error: str | None = None


def scenario_for(index: int) -> str:
    return ("contact + product", "product + human edit", "offering only")[index % 3]


def add_claim(email: dict) -> EmailDraft:
    """What a careless human might do: add an unsupported number."""
    paragraphs = email["body"].split("\n\n")
    paragraphs.insert(min(2, len(paragraphs) - 1), UNSUPPORTED_CLAIM)
    return EmailDraft(**{**email, "body": "\n\n".join(paragraphs)})


async def simulate_customer(index: int, spec: dict, lead_limit: int) -> list[LeadResult]:
    seller = spec["seller"]
    results: list[LeadResult] = []

    with SessionLocal() as db:
        organization = Organization(name=DEMO_PREFIX + seller["name"])
        db.add(organization)
        db.flush()
        user = User(
            id=uuid.uuid4(),
            email=f"demo{index + 1}@demo.example",
            organization_id=organization.id,
        )
        db.add(user)
        db.commit()
        actor = CurrentUser(id=user.id, email=user.email, organization_id=organization.id)

        company = company_service.create_company(db, organization.id, CompanyCreate(**seller))
        for product in spec["products"]:
            company_service.create_product(db, company, ProductCreate(**product))

        for lead_index, (name, website, industry, role, pain, fictional) in enumerate(
            spec["leads"][:lead_limit]
        ):
            scenario = scenario_for(lead_index)
            result = LeadResult(seller["name"], name, fictional, scenario)
            started = time.perf_counter()
            print(f"[{seller['name']}] {name}: {scenario} ...", flush=True)

            try:
                lead = lead_service.create_lead(
                    db,
                    organization.id,
                    LeadCreate(
                        company_name=name, website=website, industry=industry,
                        target_role=role, pain_point=pain,
                        recipient_name=None, recipient_email=None,
                    ),
                )

                product_id = None
                if scenario != "offering only":
                    match = await preview_solution_match(
                        SolutionMatchRequest(company_id=company.id, lead_id=lead.id), db, actor
                    )
                    product_id = match.recommended_product_id
                    result.matched_product = match.recommended_product_name
                    result.match_confidence = match.confidence

                contact = None
                if scenario == "contact + product":
                    found = await discover_contacts(
                        ContactDiscoveryRequest(lead_id=lead.id), db, actor
                    )
                    result.contacts_found = len(found.contacts)
                    usable = [
                        c for c in found.contacts
                        if c.evidence_status in ("VERIFIED", "NEEDS_REVIEW", "EXCERPT_CONSISTENT")
                    ]
                    if usable:
                        best = usable[0]
                        contact = SelectedContact(
                            name=best.name, job_title=best.job_title,
                            source_url=best.source_url, evidence_status=best.evidence_status,
                        )
                        result.contact_used = True

                run = await run_outreach_for_lead(
                    OutreachRunRequest(
                        lead_id=lead.id,
                        sender_offering=spec["offering"],
                        seller_company_id=company.id,
                        selected_product_id=product_id,
                        selected_contact=contact,
                    ),
                    db,
                    actor,
                )
                result.run_id = run.id
                result.score = run.review.get("overall_score")
                result.passed = run.approved
                result.rewrites = run.improvement_count
                result.flags = list(run.review.get("unsupported_claims") or [])
                result.ignored_flags = len(run.review.get("ignored_claims") or [])
                result.verified_findings = len(run.research.get("verified_findings") or [])
                result.subject = run.email.get("subject")
                result.body = run.email.get("body")

                if scenario == "product + human edit":
                    update_outreach_draft(
                        run.id, OutreachDraftUpdate(email=add_claim(run.email)), db, actor
                    )
                    checked = await recheck_outreach_draft(run.id, db, actor)
                    edit_review = checked.final_review or {}
                    result.edit_check_flags = list(edit_review.get("unsupported_claims") or [])
                    result.edit_check_passed = (
                        edit_review.get("overall_score", 0) >= 8 and not result.edit_check_flags
                    )
                    # The first customer approves anyway, to exercise overrides.
                    if result.edit_check_passed or index == 0:
                        approve_outreach_draft(
                            run.id, db, actor,
                            OutreachApprovalRequest(acknowledge_failed_review=True),
                        )
                        result.human_action = (
                            "approved" if result.edit_check_passed else "approved with override"
                        )
                    else:
                        result.human_action = "left for fixing"
                elif run.approved:
                    approve_outreach_draft(run.id, db, actor, None)
                    result.human_action = "approved"
                else:
                    result.human_action = "left for fixing"

                saved = db.get(OutreachRun, run.id)
                db.refresh(saved)
                result.tokens = saved.input_tokens + saved.output_tokens
                result.cost_usd = float(saved.estimated_cost_usd)
            except HTTPException as exc:
                db.rollback()
                result.error = f"{exc.status_code}: {exc.detail}"
            except Exception as exc:  # noqa: BLE001  (record and continue)
                db.rollback()
                result.error = repr(exc)

            result.seconds = round(time.perf_counter() - started, 1)
            print(
                f"[{seller['name']}] {name}: "
                + (f"ERROR {result.error}" if result.error else
                   f"run #{result.run_id}, score {result.score}, passed {result.passed}, "
                   f"{result.tokens} tokens, {result.seconds}s"),
                flush=True,
            )
            results.append(result)

    return results


def cleanup() -> None:
    """Delete every demo customer and everything they created."""
    with SessionLocal() as db:
        org_ids = list(
            db.scalars(
                select(Organization.id).where(Organization.name.startswith(DEMO_PREFIX))
            )
        )
        if not org_ids:
            print("No demo customers to delete.")
            return
        user_ids = list(db.scalars(select(User.id).where(User.organization_id.in_(org_ids))))
        company_ids = list(
            db.scalars(select(Company.id).where(Company.organization_id.in_(org_ids)))
        )
        db.execute(delete(OutreachRun).where(OutreachRun.organization_id.in_(org_ids)))
        db.execute(delete(CompanyProduct).where(CompanyProduct.company_id.in_(company_ids)))
        db.execute(delete(Company).where(Company.id.in_(company_ids)))
        db.execute(delete(Lead).where(Lead.organization_id.in_(org_ids)))
        db.execute(delete(GmailConnection).where(GmailConnection.user_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.execute(delete(Organization).where(Organization.id.in_(org_ids)))
        db.commit()
        print(f"Deleted {len(org_ids)} demo customers and their data.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--customers", type=int, default=len(CUSTOMERS))
    parser.add_argument("--leads", type=int, default=3, help="leads per customer")
    parser.add_argument("--out", type=Path, default=Path("simulation_results.json"))
    parser.add_argument("--cleanup", action="store_true", help="delete demo data and exit")
    args = parser.parse_args()

    if args.cleanup:
        cleanup()
        return

    started = time.perf_counter()
    # Customers work in parallel, like real users; each one's leads in order.
    batches = await asyncio.gather(
        *(
            simulate_customer(index, spec, args.leads)
            for index, spec in enumerate(CUSTOMERS[: args.customers])
        )
    )
    results = [result for batch in batches for result in batch]

    get_trace_provider().force_flush()

    args.out.write_text(
        json.dumps(
            {
                "seconds": round(time.perf_counter() - started, 1),
                "results": [asdict(result) for result in results],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    failed = sum(result.error is not None for result in results)
    print(f"Done: {len(results)} leads, {failed} errors. Results in {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
