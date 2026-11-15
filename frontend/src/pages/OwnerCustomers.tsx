import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, RefreshCw } from "lucide-react";

import {
  getRecentRuns,
  getUsage,
  type OrganizationUsage,
  type RunUsage,
  type UsageOverview,
} from "../api/admin";
import { Badge, Button, Card, Label, Notice, PageHeader } from "../components/ui";
import { getErrorMessage } from "../components/ui-classes";

function money(usd: number): string {
  if (usd === 0) return "$0.00";
  return usd < 0.01 ? "<$0.01" : `$${usd.toFixed(2)}`;
}

function tokens(input: number, output: number): string {
  return (input + output).toLocaleString();
}

function date(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

/** Owner Console: AI usage and cost per customer, with links to traces. */
export default function OwnerCustomers() {
  const [usage, setUsage] = useState<UsageOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setUsage(await getUsage());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load usage."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    getUsage()
      .then((data) => {
        if (!cancelled) setUsage(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load usage."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const figures = usage
    ? [
        { label: "Customers", value: usage.organizations.length.toLocaleString() },
        { label: "Drafts", value: usage.total_drafts.toLocaleString() },
        { label: "Tokens", value: usage.total_tokens.toLocaleString() },
        { label: "Estimated model cost", value: money(usage.total_estimated_cost_usd) },
      ]
    : [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Customers"
        description="AI usage and estimated cost per customer. Open a customer to see their runs and traces. Customers never see the Owner Console."
        actions={
          <Button variant="secondary" icon={RefreshCw} loading={loading} disabled={loading} onClick={() => void load()}>
            Refresh
          </Button>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}

      {usage && (
        <>
          <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line lg:grid-cols-4">
            {figures.map((figure) => (
              <div key={figure.label} className="bg-surface px-5 py-4">
                <dt><Label>{figure.label}</Label></dt>
                <dd className="mt-1 font-mono text-2xl font-bold text-ink">{figure.value}</dd>
              </div>
            ))}
          </dl>

          <Card className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-line bg-paper/60">
                <tr>
                  {["Customer", "Drafts", "Approved", "Tokens", "Est. cost", "Last draft"].map((heading) => (
                    <th key={heading} scope="col" className="px-4 py-3">
                      <Label>{heading}</Label>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {usage.organizations.map((org) => (
                  <Fragment key={org.organization_id}>
                    <CustomerRow
                      org={org}
                      open={openId === org.organization_id}
                      onToggle={() =>
                        setOpenId(openId === org.organization_id ? null : org.organization_id)
                      }
                    />
                    {openId === org.organization_id && (
                      <tr>
                        <td colSpan={6} className="bg-paper/50 px-4 py-4">
                          <CustomerRuns organizationId={org.organization_id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </Card>

          <p className="text-xs leading-5 text-muted">
            Costs are estimates from model tokens at the prices set in the backend. Web search
            calls are billed separately by OpenAI and are not included. Traces open in the OpenAI
            dashboard of the account that owns the API key.
          </p>
        </>
      )}
    </div>
  );
}

function CustomerRow({
  org,
  open,
  onToggle,
}: {
  org: OrganizationUsage;
  open: boolean;
  onToggle: () => void;
}) {
  const Chevron = open ? ChevronDown : ChevronRight;

  return (
    <tr className="align-top">
      <td className="px-4 py-3">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          className="flex items-start gap-2 text-left"
        >
          <Chevron size={16} className="mt-0.5 shrink-0 text-muted" />
          <span>
            <span className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-medium text-ink">{org.name}</span>
              {/* Same number as organization_id in the trace metadata. */}
              <span className="font-mono text-xs text-muted">Customer #{org.organization_id}</span>
            </span>
            <span className="block text-xs text-muted">
              {org.user_emails.join(", ") || "No users yet"}
            </span>
          </span>
        </button>
      </td>
      <td className="px-4 py-3 font-mono">{org.drafts}</td>
      <td className="px-4 py-3 font-mono">{org.approved_drafts}</td>
      <td className="px-4 py-3 font-mono">{tokens(org.input_tokens, org.output_tokens)}</td>
      <td className="px-4 py-3 font-mono">{money(org.estimated_cost_usd)}</td>
      <td className="px-4 py-3 text-xs text-muted">{date(org.last_draft_at)}</td>
    </tr>
  );
}

function CustomerRuns({ organizationId }: { organizationId: number }) {
  const [runs, setRuns] = useState<RunUsage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRecentRuns(organizationId)
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load runs."));
      });
    return () => {
      cancelled = true;
    };
  }, [organizationId]);

  if (error) return <Notice tone="bad">{error}</Notice>;
  if (!runs) return <p className="text-sm text-muted">Loading runs…</p>;
  if (runs.length === 0) return <p className="text-sm text-muted">No drafts yet.</p>;

  const link =
    "inline-flex items-center gap-1 font-medium text-petrol underline-offset-2 hover:underline";

  return (
    <ul className="divide-y divide-line rounded-md border border-line bg-surface">
      {runs.map((run) => (
        <li key={run.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 text-sm">
          <span className="font-mono text-ink">#{run.id}</span>
          <span className="text-xs text-muted">{date(run.created_at)}</span>
          <Badge tone={run.approved ? "ok" : "warn"}>{run.approved ? "AI passed" : "AI failed"}</Badge>
          {run.human_approved && <Badge tone="ok">Approved</Badge>}
          <span className="font-mono text-xs text-muted">
            {tokens(run.input_tokens, run.output_tokens)} tokens · {money(run.estimated_cost_usd)}
          </span>
          <span className="ml-auto flex gap-3 text-xs">
            {run.trace_url ? (
              <a href={run.trace_url} target="_blank" rel="noopener noreferrer" className={link}>
                Trace <ExternalLink size={12} />
              </a>
            ) : (
              <span className="text-muted">No trace (before tracing)</span>
            )}
            {run.recheck_trace_url && (
              <a href={run.recheck_trace_url} target="_blank" rel="noopener noreferrer" className={link}>
                Edit check <ExternalLink size={12} />
              </a>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
