import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FilePlus, Inbox } from "lucide-react";

import { getLeads, type Lead } from "../api/leads";
import { getRecentRuns, type OutreachRun } from "../api/outreach";

import EmailEditor from "../components/EmailEditor";
import GmailDraftPanel from "../components/GmailDraftPanel";
import { ContextPanel, ResearchPanel, ReviewPanel, RunDisplay } from "../components/RunDetails";
import { aiReviewStatus, humanStatus, latestReview } from "../components/run-status";
import { EmptyState, Field, Notice, PageHeader } from "../components/ui";
import { getErrorMessage, inputClass, linkButtonClass } from "../components/ui-classes";

const dotTone = {
  ok: "bg-ok",
  bad: "bg-bad",
  warn: "bg-warn",
  neutral: "bg-muted",
  accent: "bg-petrol",
} as const;

/** Page 2 of 2: review, edit, check, approve and save to Gmail. */
export default function Drafts() {
  const [params, setParams] = useSearchParams();
  const [runs, setRuns] = useState<OutreachRun[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const leadFilter = params.get("lead") ? Number(params.get("lead")) : null;

  useEffect(() => {
    let cancelled = false;
    Promise.all([getRecentRuns(), getLeads()])
      .then(([runData, leadData]) => {
        if (cancelled) return;
        setRuns(runData);
        setLeads(leadData);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load your drafts."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const leadName = (id: number) => leads.find((lead) => lead.id === id)?.company_name ?? `Lead ${id}`;
  const visible = leadFilter === null ? runs : runs.filter((run) => run.lead_id === leadFilter);
  const requested = params.get("run") ? Number(params.get("run")) : null;
  const selected = visible.find((run) => run.id === requested) ?? visible[0] ?? null;

  function setFilter(value: string) {
    const next = new URLSearchParams();
    if (value) next.set("lead", value);
    setParams(next, { replace: true });
  }

  function selectRun(run: OutreachRun) {
    const next = new URLSearchParams(params);
    next.set("run", String(run.id));
    setParams(next, { replace: true });
  }

  function handleRunUpdate(updated: OutreachRun) {
    setRuns((current) => current.map((run) => (run.id === updated.id ? updated : run)));
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Drafts"
        description="Step 2 of 2. Read each draft, fix what the AI flagged, approve it, then save it to Gmail."
        actions={
          <Link to="/outreach" className={linkButtonClass}>
            <FilePlus size={16} /> New draft
          </Link>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}

      {loading ? (
        <p className="text-sm text-muted">Loading drafts…</p>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No drafts yet"
          action={
            <Link to="/outreach" className={linkButtonClass}>
              <FilePlus size={16} /> Create your first draft
            </Link>
          }
        >
          Drafts appear here after you generate them on the New draft page.
        </EmptyState>
      ) : (
        <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
          {/* List */}
          <nav aria-label="Drafts" className="min-w-0 space-y-3 xl:sticky xl:top-6">
            <Field label="Show drafts for">
              <select
                className={inputClass}
                value={leadFilter ?? ""}
                onChange={(event) => setFilter(event.target.value)}
              >
                <option value="">All leads</option>
                {leads
                  .filter((lead) => lead.run_count > 0)
                  .map((lead) => (
                    <option key={lead.id} value={lead.id}>
                      {lead.company_name} ({lead.run_count})
                    </option>
                  ))}
              </select>
            </Field>

            {visible.length === 0 ? (
              <p className="text-sm text-muted">No drafts for this lead yet.</p>
            ) : (
              <ul className="flex gap-2 overflow-x-auto pb-1 xl:max-h-[70vh] xl:flex-col xl:overflow-y-auto xl:overflow-x-visible">
                {visible.map((run) => {
                  const active = run.id === selected?.id;
                  const statuses = [aiReviewStatus(run), humanStatus(run)];
                  return (
                    <li key={run.id} className="shrink-0 xl:shrink">
                      <button
                        type="button"
                        onClick={() => selectRun(run)}
                        aria-current={active ? "true" : undefined}
                        className={`w-56 rounded-md border px-3.5 py-3 text-left transition-colors xl:w-full ${
                          active ? "border-ink bg-ink text-white" : "border-line bg-surface hover:border-line-strong"
                        }`}
                      >
                        <span className="flex items-baseline justify-between gap-2">
                          <span className="min-w-0 truncate text-sm font-semibold">
                            {leadName(run.lead_id)}
                          </span>
                          <span className="font-mono text-xs">{latestReview(run).overall_score}/10</span>
                        </span>
                        <span className={`mt-0.5 block font-mono text-xs ${active ? "text-signal" : "text-muted"}`}>
                          Run {run.lead_run_number} · {new Date(run.created_at).toLocaleDateString()}
                        </span>
                        <span className="mt-2 flex flex-col gap-1 text-xs">
                          {statuses.map((status) => (
                            <span key={status.label} className="flex items-center gap-1.5">
                              <span className={`size-1.5 rounded-full ${dotTone[status.tone]}`} />
                              {status.label}
                            </span>
                          ))}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </nav>

          {/* Selected draft, in the order you work through it */}
          {selected && (
            <div className="min-w-0 space-y-4">
              <RunDisplay run={selected} leadName={leadName(selected.lead_id)} />
              <ReviewPanel run={selected} />
              <EmailEditor key={`editor-${selected.id}`} run={selected} onUpdate={handleRunUpdate} />
              <GmailDraftPanel
                key={`gmail-${selected.id}`}
                run={selected}
                recipientEmail={leads.find((lead) => lead.id === selected.lead_id)?.recipient_email ?? ""}
              />
              <div className="grid gap-4 2xl:grid-cols-2">
                <ContextPanel run={selected} />
                <ResearchPanel run={selected} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
