import { useEffect, useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";

import { getRecentRuns, type RunUsage } from "../api/admin";
import { Badge, Button, Card, Label, Notice, PageHeader } from "../components/ui";
import { getErrorMessage } from "../components/ui-classes";

function money(usd: number): string {
  if (usd === 0) return "$0.00";
  return usd < 0.01 ? "<$0.01" : `$${usd.toFixed(2)}`;
}

const link =
  "inline-flex items-center gap-1 font-medium text-petrol underline-offset-2 hover:underline";

/** Owner Console: the latest runs of every customer, with traces. No email content. */
export default function OwnerRuns() {
  const [runs, setRuns] = useState<RunUsage[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRecentRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load runs."));
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
      setRuns(await getRecentRuns());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load runs."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Runs"
        description="The 50 latest drafts across all customers. Open a trace to see every agent step, web search and code check."
        actions={
          <Button variant="secondary" icon={RefreshCw} loading={loading} disabled={loading} onClick={() => void reload()}>
            Refresh
          </Button>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}

      {runs && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="border-b border-line bg-paper/60">
              <tr>
                {["Run", "Customer", "Created", "Score", "AI review", "You", "Tokens · cost", "Traces"].map(
                  (heading) => (
                    <th key={heading} scope="col" className="px-4 py-3">
                      <Label>{heading}</Label>
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {runs.map((run) => (
                <tr key={run.id}>
                  <td className="px-4 py-3 font-mono text-ink">#{run.id}</td>
                  <td className="px-4 py-3">
                    <span className="block text-ink">{run.organization_name}</span>
                    <span className="font-mono text-xs text-muted">Customer #{run.organization_id}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">{new Date(run.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 font-mono">{run.overall_score ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Badge tone={run.approved ? "ok" : "warn"}>
                      {run.approved ? "Passed" : "Failed"}
                      {run.improvement_count > 0 && ` · ${run.improvement_count} rewrite${run.improvement_count > 1 ? "s" : ""}`}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {run.review_override ? (
                      <Badge tone="warn">Override</Badge>
                    ) : run.human_approved ? (
                      <Badge tone="ok">Approved</Badge>
                    ) : (
                      <span className="text-xs text-muted">Waiting</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted">
                    {(run.input_tokens + run.output_tokens).toLocaleString()} · {money(run.estimated_cost_usd)}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    <span className="flex flex-col gap-1">
                      {run.trace_url ? (
                        <a href={run.trace_url} target="_blank" rel="noopener noreferrer" className={link}>
                          Trace <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span className="text-muted">Before tracing</span>
                      )}
                      {run.recheck_trace_url && (
                        <a href={run.recheck_trace_url} target="_blank" rel="noopener noreferrer" className={link}>
                          Edit check <ExternalLink size={12} />
                        </a>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
