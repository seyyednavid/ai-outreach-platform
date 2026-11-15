import type { EmailReview, OutreachRun } from "../api/outreach";
import type { Tone } from "./ui";

export interface StatusLabel {
  label: string;
  tone: Tone;
}

/** True when you edited the draft but have not asked the AI to check it. */
export function editsUnchecked(run: OutreachRun): boolean {
  return run.final_email !== null && run.final_review === null;
}

/** The review that decides approval: of your edits once checked. */
export function latestReview(run: OutreachRun): EmailReview {
  return run.final_email !== null && run.final_review !== null
    ? run.final_review
    : run.review;
}

/** Outcome of the latest AI review — separate from any human decision. */
export function aiReviewStatus(run: OutreachRun): StatusLabel {
  if (run.final_email !== null && run.final_review !== null) {
    return run.review_passed
      ? { label: "Edits passed AI review", tone: "ok" }
      : { label: "Edits failed AI review", tone: "bad" };
  }
  if (editsUnchecked(run)) {
    return { label: "Edits not checked", tone: "warn" };
  }
  return run.approved
    ? { label: "AI review passed", tone: "ok" }
    : { label: "AI review failed", tone: "bad" };
}

/** Whether a person has signed off on the draft. */
export function humanStatus(run: OutreachRun): StatusLabel {
  if (!run.human_approved) {
    return { label: "Awaiting your approval", tone: "warn" };
  }
  return run.review_override
    ? { label: "Approved with override", tone: "warn" }
    : { label: "Approved by you", tone: "ok" };
}
