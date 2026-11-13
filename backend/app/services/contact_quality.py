
import re
from datetime import UTC, datetime

from app.schemas.contact_discovery import ContactCandidate

GENERIC_EMAIL_PREFIXES = {
    "info",
    "contact",
    "support",
    "customersupport",
    "customerservice",
    "customer.service",
    "sales",
    "admin",
    "enquiries",
    "hello",
    "office",
    "reception",
}


ROLE_KEYWORDS = {
    "retail operations": 40,
    "store operations": 40,
    "customer experience": 40,
    "customer service": 30,
    "customer operations": 35,
    "branch manager": 30,
    "store manager": 30,
    "retail": 15,
    "operations": 10,
    "procurement": 10,
    "supply chain": 3,
    "logistics": 2,
}


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def get_relevance_score(job_title: str) -> int:
    """
    Estimate role relevance to in-store queue management.

    This is a heuristic score, not a model probability.
    """
    title = normalize(job_title)

    score = 0

    for keyword, points in ROLE_KEYWORDS.items():
        if keyword in title:
            score += points

    return min(score, 100)


def extract_source_year(url: str) -> int | None:
    """
    Detect an explicit date in a URL path.

    Supports patterns like /20210305 or /2021/03/05.
    This is only a clue, not a verified publication date.
    """
    pattern = (
    r"/(20\d{2})(?:/|-)?"
    r"(0[1-9]|1[0-2])"
    r"(?:/|-)?"
    r"(0[1-9]|[12]\d|3[01])"
)

    match = re.search(pattern, url)

    if match is None:
        return None

    return int(match.group(1))


def assess_source(
    contact: ContactCandidate,
) -> tuple[str, list[str]]:
    """
    Assess the LLM-supplied evidence.

    Does not independently retrieve or verify the URL.
    """
    warnings: list[str] = []

    excerpt = normalize(contact.source_excerpt)
    name = normalize(contact.name)
    job_title = normalize(contact.job_title)

    if name not in excerpt:
        warnings.append(
            "The supplied excerpt does not contain "
            "the contact's full name."
        )

    title_words = {
        word
        for word in re.findall(r"[a-z]{4,}", job_title)
        if word not in {"head", "with", "and", "the"}
    }

    excerpt_words = set(re.findall(r"[a-z]{4,}", excerpt))

    if title_words and not title_words.intersection(
        excerpt_words
    ):
        warnings.append(
            "The supplied excerpt does not clearly "
            "support the job title."
        )

    year = extract_source_year(contact.source_url)

    if (
        year is not None
        and year <= datetime.now(UTC).year - 2
    ):
        warnings.append(
            f"Source URL suggests a publication date "
            f"in {year}; current employment is unknown."
        )

    if warnings:
        return "NEEDS_REVIEW", warnings

    return (
        "EXCERPT_CONSISTENT",
        [
            (
                "The LLM-supplied excerpt appears consistent "
                "with the name and role, but the webpage "
                "has not been independently verified."
            )
        ],
    )


def clean_and_rank_contacts(
    contacts: list[ContactCandidate],
    target_company: str,
) -> list[tuple[ContactCandidate, int, str, list[str]]]:
    """
    Remove duplicates, handle generic email addresses,
    assess supplied evidence, and rank by role relevance.
    """
    seen: set[tuple[str, str]] = set()

    results: list[
        tuple[ContactCandidate, int, str, list[str]]
    ] = []

    normalized_target = normalize(target_company)

    for contact in contacts:
        normalized_company = normalize(
            contact.company_name
        )

        # Basic company match.
        if (
            normalized_target not in normalized_company
            and normalized_company not in normalized_target
        ):
            continue

        key = (
            normalize(contact.name),
            normalized_company,
        )

        if key in seen:
            continue

        seen.add(key)

        if contact.public_work_email:
            email_prefix = (
                contact.public_work_email.split("@")[0]
                .casefold()
            )

            if email_prefix in GENERIC_EMAIL_PREFIXES:
                contact = contact.model_copy(
                    update={
                        "public_work_email": None,
                        "email_source_url": None,
                    }
                )

        score = get_relevance_score(
            contact.job_title
        )

        status, warnings = assess_source(contact)

        results.append(
            (contact, score, status, warnings)
        )

    # Most relevant business roles first.
    results.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return results
