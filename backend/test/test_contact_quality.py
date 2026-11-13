
from app.schemas.contact_discovery import ContactCandidate
from app.services.contact_quality import (
    clean_and_rank_contacts,
    get_relevance_score,
)


def make_contact(
    name: str,
    job_title: str,
    email: str | None = None,
) -> ContactCandidate:
    return ContactCandidate(
        name=name,
        job_title=job_title,
        company_name="Marks & Spencer",
        relevance_reason="Potentially relevant role",
        source_url="https://example.com/profile",
        source_excerpt=f"{name} is {job_title}.",
        public_work_email=email,
        email_source_url=(
            "https://example.com/profile" if email else None
        ),
    )


def test_retail_role_ranks_above_supply_chain():
    retail_score = get_relevance_score(
        "Retail Operations Director"
    )

    supply_chain_score = get_relevance_score(
        "Head of Supply Chain Operations"
    )

    assert retail_score > supply_chain_score


def test_duplicate_contacts_are_removed():
    contact = make_contact(
        "Example Person",
        "Retail Operations Director",
    )

    results = clean_and_rank_contacts(
        [contact, contact],
        "Marks & Spencer",
    )

    assert len(results) == 1


def test_generic_email_is_removed():
    contact = make_contact(
        "Example Person",
        "Branch Manager",
        "customersupport@example.com",
    )

    results = clean_and_rank_contacts(
        [contact],
        "Marks & Spencer",
    )

    assert results[0][0].public_work_email is None


def test_unrelated_company_is_removed():
    contact = make_contact(
        "Example Person",
        "Branch Manager",
    ).model_copy(
        update={"company_name": "Unrelated Company"}
    )

    results = clean_and_rank_contacts(
        [contact],
        "Marks & Spencer",
    )

    assert results == []
