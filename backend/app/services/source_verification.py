
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from app.schemas.contact_discovery import ReviewedContact

# Initial allowlist for public research websites.
# Add new domains only after reviewing them.
ALLOWED_HOSTS = {
    "www.bizseek.co.uk",
    "bizseek.co.uk",
    "fashionunited.uk",
    "www.fashionunited.uk",
    "theorg.com",
    "www.theorg.com",
}

MAX_RESPONSE_BYTES = 500_000
TIMEOUT_SECONDS = 8.0


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def allowed_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)

        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_HOSTS
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


async def fetch_page_text(url: str) -> str | None:
    """
    Fetch a bounded amount of HTML from an allowlisted HTTPS host.

    Redirects are intentionally disabled.
    """
    if not allowed_url(url):
        return None

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
        ) as client, client.stream("GET", url) as response:
            if response.status_code != 200:
                return None

            content_type = response.headers.get(
                "content-type", ""
            ).lower()

            if "text/html" not in content_type:
                return None

            content = bytearray()

            async for chunk in response.aiter_bytes():
                content.extend(chunk)

                if len(content) > MAX_RESPONSE_BYTES:
                    return None

        extractor = TextExtractor()

        extractor.feed(
            content.decode("utf-8", errors="replace")
        )

        return normalize(" ".join(extractor.parts))

    except (httpx.HTTPError, UnicodeError, ValueError):
        return None


async def verify_contact_source(
    contact: ReviewedContact,
) -> ReviewedContact:
    warnings = list(contact.evidence_warnings)

    if not allowed_url(contact.source_url):
        return contact.model_copy(
            update={
                "evidence_status": "REJECTED",
                "evidence_warnings": warnings + [
                    (
                        "Could not independently retrieve "
                        "the source page."
                    )
                ],
                "public_work_email": None,
                "email_source_url": None,
            }
        )

    page_text = await fetch_page_text(contact.source_url)

    if page_text is None:
        return contact.model_copy(
            update={
                "evidence_status": "NEEDS_REVIEW",
                "evidence_warnings": warnings + [
                    "Could not independently retrieve "
                    "the source page."
                ],
                "public_work_email": None,
                "email_source_url": None,
            }
        )

    name_found = normalize(contact.name) in page_text
    role_found = normalize(contact.job_title) in page_text

    if not name_found:
        warnings.append(
            "Contact name was not found in the retrieved page."
        )

    if not role_found:
        warnings.append(
            "Exact job title was not found in the retrieved page."
        )

    # Check the email using its own cited page.
    email = contact.public_work_email

    if email:
        email_url = contact.email_source_url

        if email_url == contact.source_url:
            email_text = page_text
        elif email_url and allowed_url(email_url):
            email_text = await fetch_page_text(email_url)
        else:
            email_text = None

        if (
            email_text is None
            or normalize(email) not in email_text
        ):
            warnings.append(
                "Email address was not confirmed "
                "in the independently retrieved source."
            )
            email = None
            email_url = None
    else:
        email_url = None

    # Explicit dates in the source URL are warning signals.
    # They do not prove that the person's job is current.
    old_date_warning = any(
        "current employment is unknown" in warning
        for warning in warnings
    )

    supported = (
        name_found
        and role_found
        and not old_date_warning
    )

    if supported:
        status = "VERIFIED"
        warnings.append(
            "Name and exact role appear in the fetched "
            "source. Current employment is not established."
        )
    else:
        status = "NEEDS_REVIEW"

    return contact.model_copy(
        update={
            "evidence_status": status,
            "evidence_warnings": warnings,
            "public_work_email": email,
            "email_source_url": email_url,
        }
    )
