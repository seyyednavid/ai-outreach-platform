"""
Tracing and cost tracking for agent runs.

The OpenAI Agents SDK records every agent call, tool call and model
response as spans. This module groups them into one trace per draft
and adds up token usage, so each saved run knows its trace and cost.
"""

from dataclasses import dataclass

from agents import RunConfig

from app.core.config import settings

# Bump when prompts, agents or code checks change, so traces from
# different versions can be compared.
WORKFLOW_VERSION = "outreach-2026-11-15"

TRACE_URL = "https://platform.openai.com/traces/trace?trace_id={trace_id}"


def trace_url(trace_id: str | None) -> str | None:
    return TRACE_URL.format(trace_id=trace_id) if trace_id else None


def run_config() -> RunConfig:
    """
    Settings for every agent call. With TRACE_INCLUDE_SENSITIVE_DATA
    off, traces keep timing and structure but not prompts or outputs
    (email text, names).
    """
    return RunConfig(
        trace_include_sensitive_data=settings.trace_include_sensitive_data,
    )


def trace_metadata(**values: object) -> dict[str, str]:
    """Trace metadata as strings, which is what the dashboard accepts."""
    return {
        "workflow_version": WORKFLOW_VERSION,
        **{key: str(value) for key, value in values.items() if value is not None},
    }


@dataclass
class UsageTotals:
    """Token usage added up over several agent calls."""

    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, result: object) -> None:
        """Add the usage of one Runner.run result, if it reports any."""
        usage = getattr(getattr(result, "context_wrapper", None), "usage", None)

        for field in ("requests", "input_tokens", "output_tokens"):
            value = getattr(usage, field, None)
            if isinstance(value, int):
                setattr(self, field, getattr(self, field) + value)

    @property
    def estimated_cost_usd(self) -> float:
        """
        Model tokens only, at the configured prices. Web search calls
        are billed separately and are not included.
        """
        return round(
            self.input_tokens * settings.llm_input_price_per_million / 1_000_000
            + self.output_tokens * settings.llm_output_price_per_million / 1_000_000,
            6,
        )
