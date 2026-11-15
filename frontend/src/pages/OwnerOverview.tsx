import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, RefreshCw } from "lucide-react";

import { getOwnerOverview, type OwnerOverview as Overview } from "../api/admin";
import { Button, Card, CardHeader, Label, Notice, PageHeader } from "../components/ui";
import { getErrorMessage } from "../components/ui-classes";

function money(usd: number | null): string {
  if (usd === null) return "—";
  if (usd === 0) return "$0.00";
  return usd < 0.01 ? "<$0.01" : `$${usd.toFixed(2)}`;
}

function percent(part: number, whole: number): string {
  return whole > 0 ? `${Math.round((part / whole) * 100)}%` : "—";
}

/** Owner Console home: the health of the product across all customers. */
export default function OwnerOverview() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOwnerOverview()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load the overview."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      setData(await getOwnerOverview());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load the overview."));
    } finally {
      setLoading(false);
    }
  }

  const q = data?.quality;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Owner console"
        description="How the product is doing across all customers: activity, model cost and the quality of the AI. Customers never see this console."
        actions={
          <Button variant="secondary" icon={RefreshCw} loading={loading} disabled={loading} onClick={() => void reload()}>
            Refresh
          </Button>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}

      {data && q && (
        <>
          <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line lg:grid-cols-4">
            <Figure label="Customers" value={data.customers} note={`${data.users} signed-in users`} />
            <Figure label="Drafts" value={data.drafts} note={`${data.drafts_last_7_days} in the last 7 days`} />
            <Figure
              label="Model cost"
              value={money(data.estimated_cost_usd)}
              note={`${data.total_tokens.toLocaleString()} tokens`}
            />
            <Figure
              label="Cost per draft"
              value={money(data.average_cost_per_draft_usd)}
              note="drafts with recorded usage"
            />
          </dl>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-5 md:p-6">
              <CardHeader
                title="AI quality"
                description="A draft passes with a score of 8 or more and no flags left."
              />
              <dl className="mt-5 grid grid-cols-2 gap-4">
                <Stat label="AI pass rate" value={percent(q.ai_passed, q.drafts)} note={`${q.ai_passed} of ${q.drafts} drafts`} />
                <Stat
                  label="Passed first time"
                  value={percent(q.first_try_passed, q.drafts)}
                  note="no rewrite needed"
                />
                <Stat label="Average score" value={q.average_score?.toFixed(1) ?? "—"} note="out of 10" />
                <Stat label="Average rewrites" value={q.average_rewrites?.toFixed(2) ?? "—"} note="maximum 2" />
              </dl>
            </Card>

            <Card className="p-5 md:p-6">
              <CardHeader
                title="Guardrails and people"
                description="Where code corrected the AI, and where people stepped in."
              />
              <dl className="mt-5 grid grid-cols-2 gap-4">
                <Stat
                  label="Reviewer flags dropped by code"
                  value={q.flags_ignored_by_code}
                  note="quote not in the email"
                />
                <Stat
                  label="Flags left in final reviews"
                  value={q.flags_kept}
                  note={`${q.placeholder_flags} placeholders · ${q.missing_signature_flags} no signature`}
                />
                <Stat
                  label="Edited by people"
                  value={q.edited_by_human}
                  note={`${q.edits_checked_by_ai} checked by AI · ${q.edits_failed_check} failed`}
                />
                <Stat
                  label="Approved"
                  value={q.human_approved}
                  note={`${q.overrides} despite a failed review`}
                  warn={q.overrides > 0}
                />
              </dl>
            </Card>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link to="/owner/customers" className="inline-flex items-center gap-1 text-sm font-semibold text-petrol hover:underline">
              Usage per customer <ArrowRight size={14} />
            </Link>
            <Link to="/owner/runs" className="inline-flex items-center gap-1 text-sm font-semibold text-petrol hover:underline">
              Latest runs and traces <ArrowRight size={14} />
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function Figure({ label, value, note }: { label: string; value: number | string; note: string }) {
  return (
    <div className="bg-surface px-5 py-4">
      <dt><Label>{label}</Label></dt>
      <dd className="mt-1 font-mono text-2xl font-bold text-ink">{value}</dd>
      <dd className="mt-0.5 text-xs text-muted">{note}</dd>
    </div>
  );
}

function Stat({
  label,
  value,
  note,
  warn = false,
}: {
  label: string;
  value: number | string;
  note: string;
  warn?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className={`mt-0.5 font-mono text-xl font-bold ${warn ? "text-warn" : "text-ink"}`}>{value}</dd>
      <dd className="text-xs text-muted">{note}</dd>
    </div>
  );
}
