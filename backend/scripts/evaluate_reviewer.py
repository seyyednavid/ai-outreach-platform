"""
Evaluate the Reviewer against fixed test cases with known answers.

Runs the real Reviewer agent and the real code checks (quote check,
placeholder check, pass rule) on every case, several times, and reports:

- catch rate:   planted problems that were flagged
- false alarms: supported emails that got a flag
- consistency:  cases with the same outcome on every run

    uv run python -m scripts.evaluate_reviewer                      # 30 cases x 3 runs
    uv run python -m scripts.evaluate_reviewer --runs 1             # quick check
    uv run python -m scripts.evaluate_reviewer --min-catch 0.9 --max-false-alarm 0.1   # for CI

Costs a few cents: only the Reviewer runs, without web search.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from agents.tracing import get_trace_provider

import app.main  # noqa: F401  (sets the OpenAI key for agents and tracing)
from app.core.tracing import UsageTotals
from app.services.outreach_service import build_signature
from app.workflows import outreach_workflow
from app.workflows.outreach_workflow import passes_review, review_email
from evals.reviewer_cases import (
    CASES,
    OFFERING,
    RESEARCH,
    SELLER,
    ReviewerCase,
    build_context,
    build_email,
)


def outcome(case: ReviewerCase, flags: list[str]) -> bool:
    """True when the Reviewer (with the code checks) got this case right."""
    if case.expected == "pass":
        return not flags
    return any(case.catch.casefold() in flag.casefold() for flag in flags)


async def evaluate_once(case: ReviewerCase, usage: UsageTotals, limit: asyncio.Semaphore) -> dict:
    async with limit:
        review = await review_email(
            draft=build_email(case),
            research=RESEARCH,
            sender_offering=OFFERING,
            context=build_context(case),
            usage=usage,
            signature=build_signature(SELLER),
        )
    return {
        "correct": outcome(case, review.unsupported_claims),
        "passed": passes_review(review),
        "score": review.overall_score,
        "flags": review.unsupported_claims,
        "ignored": review.ignored_claims,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("reviewer_eval_results.json"))
    parser.add_argument("--min-catch", type=float, default=None, help="fail below this catch rate")
    parser.add_argument("--max-false-alarm", type=float, default=None, help="fail above this rate")
    parser.add_argument("--model", default=None, help="try another model, e.g. gpt-4.1")
    args = parser.parse_args()

    if args.model:
        # review_email uses this module-level agent.
        outreach_workflow.reviewer_agent = outreach_workflow.reviewer_agent.clone(model=args.model)
    model = outreach_workflow.reviewer_agent.model

    usage = UsageTotals()
    limit = asyncio.Semaphore(args.concurrency)
    started = time.perf_counter()

    runs = await asyncio.gather(
        *(
            asyncio.gather(*(evaluate_once(case, usage, limit) for _ in range(args.runs)))
            for case in CASES
        )
    )
    get_trace_provider().force_flush()

    bad = [(c, r) for c, r in zip(CASES, runs, strict=True) if c.expected == "flag"]
    good = [(c, r) for c, r in zip(CASES, runs, strict=True) if c.expected == "pass"]

    def rate(pairs, predicate):
        attempts = [run for _, results in pairs for run in results]
        return sum(predicate(run) for run in attempts) / len(attempts)

    catch_rate = rate(bad, lambda run: run["correct"])
    false_alarm_rate = rate(good, lambda run: not run["correct"])
    consistent = sum(len({run["correct"] for run in results}) == 1 for _, results in zip(CASES, runs, strict=True))

    print(f"\nReviewer evaluation ({model}): {len(CASES)} cases x {args.runs} runs\n")
    print(f"{'case':34} {'expect':6}  runs")
    for case, results in zip(CASES, runs, strict=True):
        marks = " ".join("✓" if run["correct"] else "✗" for run in results)
        print(f"{case.id:34} {case.expected:6}  {marks}")
        for run in results:
            if not run["correct"]:
                detail = run["flags"] if case.expected == "pass" else (run["flags"] or "(no flags)")
                print(f"{'':42}↳ {str(detail)[:150]}")
                break

    summary = {
        "model": model,
        "cases": len(CASES),
        "runs_per_case": args.runs,
        "catch_rate": round(catch_rate, 3),
        "false_alarm_rate": round(false_alarm_rate, 3),
        "consistency": round(consistent / len(CASES), 3),
        "tokens": usage.input_tokens + usage.output_tokens,
        "estimated_cost_usd": usage.estimated_cost_usd,
        "seconds": round(time.perf_counter() - started, 1),
    }
    print(
        f"\nProblems caught:      {catch_rate:.0%}  of {len(bad)} planted problems"
        f"\nFalse alarms:         {false_alarm_rate:.0%}  of {len(good)} supported emails"
        f"\nSame result each run: {consistent}/{len(CASES)} cases"
        f"\nCost:                 ${usage.estimated_cost_usd:.3f}  ({summary['seconds']} s)"
    )

    args.out.write_text(
        json.dumps(
            {"summary": summary,
             "cases": [{"id": c.id, "expected": c.expected, "runs": r} for c, r in zip(CASES, runs, strict=True)]},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    failed = (args.min_catch is not None and catch_rate < args.min_catch) or (
        args.max_false_alarm is not None and false_alarm_rate > args.max_false_alarm
    )
    if failed:
        print("\nFAILED: below the required quality.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
