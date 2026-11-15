import {
  ExternalLink,
  FileSearch,
  ListChecks,
  Package,
  ShieldAlert,
  UserRound,
} from "lucide-react";

import type { OutreachRun } from "../api/outreach";
import { aiReviewStatus, editsUnchecked, humanStatus, latestReview } from "./run-status";
import { Badge, Card, CardHeader, Label } from "./ui";

/**
 * Call-forward style header for the run under review.
 * Echoes the "Now serving · counter 4" displays the seller ships.
 */
export function RunDisplay({ run, leadName }: { run: OutreachRun; leadName?: string }) {
  const ai = aiReviewStatus(run);
  const human = humanStatus(run);
  const review = latestReview(run);
  const claims = review.unsupported_claims.length;

  return (
    <div className="overflow-hidden rounded-lg bg-display text-white ring-1 ring-black/5">
      <div className="flex flex-wrap items-stretch">
        <div className="flex items-baseline gap-4 px-5 py-4 md:px-6">
          <div>
            <p className="font-mono text-[11px] font-bold uppercase tracking-[0.14em] text-white/45">
              Now reviewing
            </p>
            <p className="mt-1 font-mono text-4xl font-bold leading-none tracking-tight text-signal [text-shadow:0_0_18px_rgb(244_176_74/0.35)]">
              Run {run.lead_run_number}
            </p>
            <p className="mt-1.5 font-mono text-[11px] text-white/45">
              for this lead · #{run.id} overall
            </p>
          </div>
        </div>

        <dl className="grid flex-1 grid-cols-3 border-t border-white/10 sm:border-l sm:border-t-0">
          <div className="px-3 py-4 sm:px-4">
            <dt className="font-mono text-[11px] uppercase tracking-[0.1em] text-white/45">
              AI score
            </dt>
            <dd className="mt-1 font-mono text-2xl font-bold">
              {review.overall_score}
              <span className="text-sm text-white/40">/10</span>
            </dd>
          </div>
          <div className="border-l border-white/10 px-3 py-4 sm:px-4">
            <dt className="font-mono text-[11px] uppercase tracking-[0.1em] text-white/45">
              Flagged claims
            </dt>
            <dd
              className={`mt-1 font-mono text-2xl font-bold ${
                claims > 0 ? "text-[#ff8a7a]" : ""
              }`}
            >
              {claims}
            </dd>
          </div>
          <div className="border-l border-white/10 px-3 py-4 sm:px-4">
            <dt className="font-mono text-[11px] uppercase tracking-[0.1em] text-white/45">
              Rewrites
            </dt>
            <dd className="mt-1 font-mono text-2xl font-bold">
              {run.improvement_count}
              <span className="text-sm text-white/40">/2</span>
            </dd>
          </div>
        </dl>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-white/10 bg-white/[0.03] px-5 py-2.5 md:px-6">
        <Badge tone={ai.tone}>{ai.label}</Badge>
        <Badge tone={human.tone}>{human.label}</Badge>
        <span className="ml-auto text-xs text-white/50">
          {leadName && <>{leadName} · </>}
          {new Date(run.created_at).toLocaleString()}
        </span>
      </div>
    </div>
  );
}

export function ReviewPanel({ run }: { run: OutreachRun }) {
  const review = latestReview(run);
  const reviewingEdits = review === run.final_review;
  const scores: [string, number][] = [
    ["Personalisation", review.personalization],
    ["Clarity", review.clarity],
    ["Relevance", review.relevance],
    ["Call to action", review.cta_quality],
  ];

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        icon={ListChecks}
        title={reviewingEdits ? "AI review of your edits" : "AI review"}
        description={
          reviewingEdits
            ? "Checked against the same research and context as the original draft."
            : editsUnchecked(run)
              ? "These scores are for the AI's draft, not your edits. Use “Check my edits with AI” below the email."
              : "Passes only with 8/10 or more and no flagged claims."
        }
      />

      {review.unsupported_claims.length > 0 && (
        <div className="mt-5 rounded-md border border-bad/20 bg-bad-wash p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-bad">
            <ShieldAlert size={16} />
            Check these claims before approving
          </p>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-ink">
            {review.unsupported_claims.map((claim, index) => (
              <li key={index}>{claim}</li>
            ))}
          </ul>
        </div>
      )}

      {(review.ignored_claims?.length ?? 0) > 0 && (
        <details className="mt-3 rounded-md border border-line px-4 py-3 text-sm">
          <summary className="cursor-pointer text-ink-soft">
            {review.ignored_claims!.length} flag{review.ignored_claims!.length === 1 ? "" : "s"} ignored:
            not in the email, or marked as supported
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 leading-6 text-muted">
            {review.ignored_claims!.map((claim, index) => (
              <li key={index}>{claim}</li>
            ))}
          </ul>
        </details>
      )}

      <dl className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-4">
        {scores.map(([label, score]) => (
          <div key={label} className="bg-surface px-3 py-2.5">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-0.5 font-mono text-lg font-bold">
              {score}
              <span className="text-xs font-medium text-muted">/10</span>
            </dd>
          </div>
        ))}
      </dl>

      {review.improvement_suggestions.length > 0 && (
        <div className="mt-5">
          <Label>Suggestions</Label>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-ink-soft">
            {review.improvement_suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}

      {reviewingEdits && (
        <details className="mt-5 rounded-md border border-line px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium text-ink-soft">
            Review of the AI's original draft — {run.review.overall_score}/10,{" "}
            {run.review.unsupported_claims.length} flagged
          </summary>
          {run.review.unsupported_claims.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 leading-6 text-muted">
              {run.review.unsupported_claims.map((claim, index) => (
                <li key={index}>{claim}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-muted">No flagged claims.</p>
          )}
        </details>
      )}
    </Card>
  );
}

export function ContextPanel({ run }: { run: OutreachRun }) {
  const context = run.context;

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        icon={Package}
        title="What the AI was given"
        description="Saved with the run, so you can see why it wrote what it wrote."
      />

      {context === null ? (
        <p className="mt-4 text-sm text-muted">
          This run was created before context was recorded.
        </p>
      ) : (
        <dl className="mt-5 space-y-4 text-sm">
          <div>
            <dt><Label>Seller and product</Label></dt>
            <dd className="mt-1 text-ink">
              {context.selected_product
                ? `${context.seller_company?.name ?? "Unknown seller"} — ${context.selected_product.name}`
                : "No catalogue product. The AI used your offering text only."}
            </dd>
          </div>

          <div>
            <dt><Label>Signed by</Label></dt>
            <dd className="mt-1 text-ink">
              {context.seller_company?.sender_name
                ? `${context.seller_company.sender_name} · asks for ${
                    context.seller_company.cta_type === "email" ? "an email reply" : "a phone call"
                  }`
                : "No sender details. Add them in My Company."}
            </dd>
          </div>

          <div>
            <dt><Label>Contact</Label></dt>
            <dd className="mt-1">
              {context.selected_contact ? (
                <div className="flex flex-wrap items-center gap-2">
                  <UserRound size={15} className="text-muted" />
                  <span className="text-ink">{context.selected_contact.name}</span>
                  <span className="text-muted">
                    reported as {context.selected_contact.reported_job_title}
                  </span>
                  <Badge tone="warn">Not verified</Badge>
                  <a
                    href={context.selected_contact.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-medium text-petrol hover:underline"
                  >
                    Source <ExternalLink size={12} />
                  </a>
                </div>
              ) : (
                <span className="text-ink">No contact. The email uses a neutral greeting.</span>
              )}
            </dd>
          </div>

          <div>
            <dt><Label>Your offering</Label></dt>
            <dd className="mt-1 leading-6 text-ink-soft">{context.sender_offering}</dd>
          </div>
        </dl>
      )}
    </Card>
  );
}

export function ResearchPanel({ run }: { run: OutreachRun }) {
  const { research } = run;

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        icon={FileSearch}
        title={`Research on ${research.company_name}`}
        description="Collected by the AI from public sources. Open the source before relying on a claim."
      />

      {research.verified_findings.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No sourced findings were returned.</p>
      ) : (
        <ul className="mt-5 divide-y divide-line border-y border-line">
          {research.verified_findings.map((finding, index) => (
            <li key={index} className="flex gap-4 py-3 text-sm">
              <p className="flex-1 leading-6 text-ink">{finding.claim}</p>
              <a
                href={finding.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-fit shrink-0 items-center gap-1 pt-0.5 text-xs font-medium text-petrol hover:underline"
              >
                Source <ExternalLink size={12} />
              </a>
            </li>
          ))}
        </ul>
      )}

      {research.potential_pain_points.length > 0 && (
        <div className="mt-5">
          <Label>Possible needs — unconfirmed</Label>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-ink-soft">
            {research.potential_pain_points.map((point, index) => (
              <li key={index}>{point}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
