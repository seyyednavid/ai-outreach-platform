"""
Fixed test cases for the Reviewer, each with the correct answer.

Every case is the same base email with one sentence added. "flag" cases
add a problem the Reviewer must catch; "pass" cases add a sentence the
evidence supports, which must not be flagged.

The target company is fictional, so the Reviewer can only judge by the
evidence given here, not by what the model knows about real companies.
"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Literal

from app.agents.research_agent import ResearchFinding, ResearchReport
from app.agents.writer_agent import EmailDraft
from app.schemas.outreach import (
    OutreachRunContext,
    RunContactSnapshot,
    RunProductSnapshot,
    RunSellerSnapshot,
)
from app.services.outreach_service import build_agent_context, build_signature

OFFERING = "Queue management systems that reduce waiting at tills and service counters."

LEAD = SimpleNamespace(
    company_name="Harbour & Finch Pharmacy",
    target_role="Head of Store Operations",
    pain_point="Possible queues at prescription counters at peak times",
)

RESEARCH = ResearchReport(
    company_name="Harbour & Finch Pharmacy",
    industry="Pharmacy retail",
    verified_findings=[
        ResearchFinding(
            claim="Harbour & Finch operates 1,912 pharmacies across the UK.",
            source_url="https://www.harbourandfinch.example/about",
        ),
        ResearchFinding(
            claim="Harbour & Finch launched click-and-collect for prescriptions in 2026.",
            source_url="https://www.harbourandfinch.example/news/click-and-collect",
        ),
        ResearchFinding(
            claim="Harbour & Finch pharmacies offer free blood pressure checks.",
            source_url="https://www.harbourandfinch.example/services",
        ),
    ],
    potential_pain_points=["Possible queues at prescription counters at peak times"],
    suggested_solution="A virtual queue for prescription collection",
    personalization_angle="The new click-and-collect service for prescriptions",
)

SELLER = RunSellerSnapshot(
    id=1,
    name="QueueWise Systems",
    industry="Queue management",
    description=(
        "QueueWise designs queue management for retail and pharmacy counters: "
        "virtual queues and call-forward displays."
    ),
    target_customers="UK retailers, pharmacies and service counters",
    differentiators="Installed in under a week; works alongside existing tills",
    sender_name="Priya Shah",
    sender_job_title="Head of Partnerships",
    sign_off="Kind regards",
    sender_email="priya.shah@example.com",
    sender_phone="+44 20 7946 0101",
    cta_type="call",
)

PRODUCT = RunProductSnapshot(
    id=1,
    name="Virtual Queue App",
    description="Customers join a queue from their phone and get a text when it is their turn.",
    features=["Join by QR code", "SMS alerts", "Live wait times"],
    use_cases=["Pharmacy prescription collection", "Click and collect desks"],
)

CONTACT = RunContactSnapshot(
    name="Sarah Patel",
    reported_job_title="Head of Store Operations",
    source_url="https://www.harbourandfinch.example/team",
    client_evidence_status="NEEDS_REVIEW",
    backend_verification_status="NOT_VERIFIED",
)

CTA = "Would a short call next week be useful to see whether it could fit your pharmacies?"

OPENING = (
    "I noticed that Harbour & Finch recently launched click-and-collect "
    "for prescriptions across its pharmacies."
)
PRODUCT_PARAGRAPH = (
    "QueueWise's Virtual Queue App lets customers join a queue from their phone "
    "and get a text when it is their turn, so they can wait comfortably instead "
    "of standing at the counter."
)


@dataclass(frozen=True)
class ReviewerCase:
    id: str
    expected: Literal["pass", "flag"]
    sentence: str | None
    why: str
    # For "flag" cases: words that must appear in a kept flag.
    catch: str | None = None
    with_contact: bool = True


CASES = [
    # ---- Supported by the evidence: must NOT be flagged ----------------
    ReviewerCase("good-base", "pass", None, "The base email, every claim supported."),
    ReviewerCase("good-rounded-number", "pass",
                 "Harbour & Finch now runs more than 1,900 pharmacies across the UK.",
                 "Rounded down from 1,912 in the research."),
    ReviewerCase("good-nearly-number", "pass",
                 "Harbour & Finch has nearly 2,000 pharmacies across the UK.",
                 "“Nearly 2,000” for 1,912 is a true rounding."),
    ReviewerCase("good-hedged-benefit", "pass",
                 "A virtual queue could help keep prescription counters calmer at busy times.",
                 "Hedged (“could”), not a factual claim."),
    ReviewerCase("good-catalogue-features", "pass",
                 "Customers join by scanning a QR code, and staff can see live wait times.",
                 "Both are catalogue features."),
    ReviewerCase("good-differentiators", "pass",
                 "It works alongside your existing tills and is installed in under a week.",
                 "Exactly the seller's differentiators."),
    ReviewerCase("good-use-cases", "pass",
                 "It is designed for pharmacy prescription collection and click-and-collect desks.",
                 "Catalogue use cases."),
    ReviewerCase("good-research-fact", "pass",
                 "I also saw that your pharmacies offer free blood pressure checks.",
                 "A verified research finding."),
    ReviewerCase("good-conditional-need", "pass",
                 "If prescription counters get busy at peak times, customers could wait away from the queue instead.",
                 "The need is conditional, not stated as fact."),
    ReviewerCase("good-sms-feature", "pass",
                 "The app sends customers a text message when it is their turn.",
                 "SMS alerts are a catalogue feature."),
    ReviewerCase("good-offering", "pass",
                 "QueueWise provides queue management systems that reduce waiting at tills and service counters.",
                 "The seller's own offering text."),
    ReviewerCase("good-qr-feature", "pass",
                 "Customers can join the queue by scanning a QR code in store.",
                 "A catalogue feature."),
    ReviewerCase("good-combined", "pass",
                 "With nearly 2,000 pharmacies and the new click-and-collect service, a virtual queue could help at busy counters.",
                 "Rounded fact, research fact and a hedged benefit."),
    ReviewerCase("good-no-contact", "pass", None,
                 "No contact selected: neutral greeting, nothing to flag.", with_contact=False),

    # ---- Planted problems: MUST be flagged -----------------------------
    ReviewerCase("bad-invented-statistic", "flag",
                 "Our clients see waiting times fall by 40% on average.",
                 "No evidence for any statistic.", catch="40%"),
    ReviewerCase("bad-invented-customers", "flag",
                 "We already work with more than 200 UK pharmacies.",
                 "Customer count not in any evidence.", catch="200"),
    ReviewerCase("bad-job-title", "flag",
                 "As Head of Store Operations, you will know how busy counters can get.",
                 "States the contact's unverified job title.", catch="Head of Store Operations"),
    ReviewerCase("bad-embellished-integration", "flag",
                 "It integrates seamlessly with your existing till system.",
                 "Catalogue says “works alongside”, not “integrates seamlessly”.", catch="seamlessly"),
    ReviewerCase("bad-embellished-install", "flag",
                 "It can be installed in a single day.",
                 "Seller says “under a week”, not one day.", catch="single day"),
    ReviewerCase("bad-need-as-fact", "flag",
                 "Your pharmacies have long queues at the prescription counter every afternoon.",
                 "An unverified pain point stated as fact.", catch="long queues"),
    ReviewerCase("bad-invented-relationship", "flag",
                 "It was great to meet your team at the Pharmacy Show last month.",
                 "An invented previous meeting.", catch="Pharmacy Show"),
    ReviewerCase("bad-wrong-number", "flag",
                 "Harbour & Finch now runs more than 3,000 pharmacies across the UK.",
                 "Research says 1,912.", catch="3,000"),
    ReviewerCase("bad-invented-feature", "flag",
                 "The app also predicts staffing needs using AI.",
                 "Not a catalogue feature.", catch="staffing"),
    ReviewerCase("bad-named-integration", "flag",
                 "It connects directly to your EPOS and NHS prescription systems.",
                 "Named integrations not in the catalogue.", catch="EPOS"),
    ReviewerCase("bad-invented-award", "flag",
                 "QueueWise won Retail Technology of the Year in 2025.",
                 "An invented award.", catch="Retail Technology"),
    ReviewerCase("bad-named-customers", "flag",
                 "Leading chains such as Boots and Superdrug already use our system.",
                 "Invented named customers.", catch="Superdrug"),
    ReviewerCase("bad-guaranteed-outcome", "flag",
                 "This will cut your waiting times in half.",
                 "A guaranteed, unsupported result.", catch="in half"),
    ReviewerCase("bad-placeholder", "flag",
                 "I would be happy to send you [case study link] before we speak.",
                 "Unfilled placeholder (caught by code).", catch="[case study link]"),
    ReviewerCase("bad-wrong-research", "flag",
                 "I saw that Harbour & Finch opened 50 new pharmacies this year.",
                 "Not in the research.", catch="50 new"),
    ReviewerCase("bad-invented-certification", "flag",
                 "The system is fully certified by the NHS.",
                 "An invented certification.", catch="certified"),
]


def build_email(case: ReviewerCase) -> EmailDraft:
    """The base email, with the case's sentence as its own paragraph."""
    greeting = "Hi Sarah," if case.with_contact else "Hello,"
    paragraphs = [greeting, OPENING, PRODUCT_PARAGRAPH]
    if case.sentence:
        paragraphs.append(case.sentence)
    paragraphs.append(CTA)

    body = "\n\n".join(paragraphs) + "\n\n" + build_signature(SELLER)
    return EmailDraft(
        subject="Shorter waits at Harbour & Finch prescription counters",
        body=body,
        call_to_action=CTA,
    )


def build_context(case: ReviewerCase) -> dict[str, object]:
    """Built by the app's own function, exactly as for a real draft."""
    snapshot = OutreachRunContext(
        sender_offering=OFFERING,
        seller_company=SELLER,
        selected_product=PRODUCT,
        selected_contact=CONTACT if case.with_contact else None,
    )
    return build_agent_context(LEAD, snapshot)
