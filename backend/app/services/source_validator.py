
from urllib.parse import urlparse

from app.agents.research_agent import ResearchFinding


def validate_source(finding: ResearchFinding) -> bool:
    """Check whether a finding has a plausible public source URL."""
    parsed = urlparse(finding.source_url)

    if parsed.scheme != "https":
        return False

    if not parsed.hostname:
        return False

    if parsed.username or parsed.password:
        return False

    if not finding.claim.strip():
        return False

    return bool(finding.claim.strip())
