
from app.schemas.contact_discovery import ContactCandidate

GENERIC_EMAIL_PREFIXES = {
    "info",
    "contact",
    "support",
    "customersupport",
    "customer.service",
    "customerservice",
    "sales",
    "admin",
    "enquiries",
    "hello",
    "office",
    "reception",
}


def clean_contacts(
    contacts: list[ContactCandidate],
    target_company: str,
) -> list[ContactCandidate]:
    unique_contacts: list[ContactCandidate] = []
    seen: set[tuple[str, str]] = set()

    for contact in contacts:
        # Remove contacts assigned to an unrelated company.
        normalized_company = contact.company_name.casefold().strip()
        normalized_target = target_company.casefold().strip()

        if (
            normalized_target not in normalized_company
            and normalized_company not in normalized_target
        ):
            continue

        # Remove duplicate people.
        key = (
            contact.name.casefold().strip(),
            contact.company_name.casefold().strip(),
        )

        if key in seen:
            continue

        seen.add(key)

        # Never attach a generic company inbox to an individual.
        if contact.public_work_email:
            prefix = contact.public_work_email.split("@")[0].casefold()

            if prefix in GENERIC_EMAIL_PREFIXES:
                contact = contact.model_copy(
                    update={
                        "public_work_email": None,
                        "email_source_url": None,
                    }
                )

        unique_contacts.append(contact)

    return unique_contacts
