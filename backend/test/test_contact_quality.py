
import pytest

from app.schemas.contact_discovery import ContactCandidate
from app.services.contact_quality import (
    clean_and_rank_contacts,
    get_relevance_score,
    looks_like_person,
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


def test_seniority_and_target_role_raise_the_score():
    plain = get_relevance_score("Retail Director")
    matched = get_relevance_score("Retail Director", target_role="Retail Operations Manager")

    assert plain > get_relevance_score("Retail Assistant")  # seniority counts
    assert matched == plain + 25  # shares "retail" with the wanted role
    assert get_relevance_score("Supply Chain Analyst", "Retail Operations Manager") < 10


@pytest.mark.parametrize(
    "name",
    ["Customer Service Team", "Waitrose", "Waitrose & Partners", "Support Desk", "J0hn Smith"],
)
def test_teams_and_companies_are_not_contacts(name):
    assert looks_like_person(name) is False


@pytest.mark.parametrize("name", ["Jane Doe", "Mary-Ann O'Neil", "José García López"])
def test_named_people_are_contacts(name):
    assert looks_like_person(name) is True
