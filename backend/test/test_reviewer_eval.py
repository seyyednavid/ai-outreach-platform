"""
The evaluation cases themselves, and the code they rely on.

No model calls: these run in CI for free. The evaluation itself
(scripts/evaluate_reviewer.py) calls the real Reviewer.
"""

import json
from datetime import date

from app.agents.writer_agent import EmailDraft
from app.services.outreach_service import build_signature
from app.workflows.outreach_workflow import build_prompt, without_signature
from evals.reviewer_cases import CASES, SELLER, build_context, build_email


def test_cases_are_balanced_and_unique():
    ids = [case.id for case in CASES]

    assert len(ids) == len(set(ids)) == 30
    assert sum(case.expected == "flag" for case in CASES) == 16
    assert sum(case.expected == "pass" for case in CASES) == 14


def test_every_planted_problem_is_in_its_email():
    for case in CASES:
        if case.expected == "flag":
            assert case.catch, case.id
            assert case.catch in build_email(case).body, case.id
        else:
            assert case.catch is None, case.id


def test_cases_use_the_apps_own_context():
    with_contact = build_context(next(c for c in CASES if c.with_contact))
    without_contact = build_context(next(c for c in CASES if not c.with_contact))

    assert with_contact["selected_contact"]["name"] == "Sarah Patel"
    # The job title never reaches the agents.
    assert "Head of Store Operations" not in json.dumps(with_contact["selected_contact"])
    assert "selected_contact" not in without_contact


def test_signature_is_not_sent_for_review():
    signature = build_signature(SELLER)
    email = build_email(CASES[0])

    reviewed = without_signature(email, signature)

    assert signature not in reviewed.body
    assert reviewed.body.endswith("fit your pharmacies?")
    assert "Head of Partnerships" not in reviewed.body


def test_a_signature_changed_by_a_human_is_reviewed():
    signature = build_signature(SELLER)
    edited = EmailDraft(
        subject="Shorter waits at your counters",
        body="Hello,\n\nA short note about queues.\n\nKind regards,\nPriya, Head of Everything",
        call_to_action="Would a short call help?",
    )

    assert without_signature(edited, signature) == edited
    assert without_signature(edited, None) == edited


def test_prompts_tell_the_agents_todays_date():
    prompt = build_prompt("Review this email.", email={"subject": "Hi"})

    assert f'"today": "{date.today().isoformat()}"' in prompt
    assert '"email": {' in prompt
