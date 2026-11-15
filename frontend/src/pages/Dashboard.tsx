import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, RefreshCw } from "lucide-react";

import { getDashboardStats, type DashboardStats } from "../api/dashboard";
import { Button, Card, Label, Notice, PageHeader } from "../components/ui";
import { getErrorMessage } from "../components/ui-classes";

const steps = [
  { title: "Add your company", body: "Your products, and your name and contact details for the signature.", to: "/company" },
  { title: "Add a lead", body: "The target company, the role you want and a possible need.", to: "/leads" },
  { title: "Write a new draft", body: "Choose a lead and product. The AI researches, writes and checks it.", to: "/outreach" },
  { title: "Review and approve", body: "Fix what the AI flagged, approve, then save it as a Gmail draft.", to: "/drafts" },
];

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDashboardStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load activity."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setStats(await getDashboardStats());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load activity."));
    } finally {
      setLoading(false);
    }
  }

  const approvalRate =
    stats && stats.total_outreach_runs > 0
      ? Math.round((stats.human_approved_emails / stats.total_outreach_runs) * 100)
      : null;

  const figures = [
    { label: "Leads", value: stats?.total_leads, note: "companies to reach" },
    { label: "Drafts generated", value: stats?.total_outreach_runs, note: "AI workflow runs" },
    {
      label: "Approved by you",
      value: stats?.human_approved_emails,
      note: approvalRate === null ? "of generated drafts" : `${approvalRate}% of generated drafts`,
    },
    {
      label: "Average AI score",
      value: stats ? stats.average_review_score.toFixed(1) : undefined,
      note: "out of 10 · passing is 8",
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Your outreach activity so far."
        actions={
          <Button variant="secondary" icon={RefreshCw} loading={loading} disabled={loading} onClick={() => void load()}>
            Refresh
          </Button>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}

      <Card as="div" className="grid grid-cols-2 gap-px overflow-hidden bg-line lg:grid-cols-4">
        {figures.map((figure) => (
          <div key={figure.label} className="bg-surface px-5 py-5 md:px-6">
            <Label>{figure.label}</Label>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-ink md:text-4xl">
              {figure.value ?? (loading ? "··" : "—")}
            </p>
            <p className="mt-1 text-xs text-muted">{figure.note}</p>
          </div>
        ))}
      </Card>

      <section aria-labelledby="flow-heading">
        <h2 id="flow-heading" className="font-display text-xl font-bold tracking-tight">
          How it works
        </h2>
        <ol className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <li key={step.title}>
              <Link
                to={step.to}
                className="group flex h-full flex-col rounded-lg border border-line bg-surface p-5 transition-colors hover:border-petrol"
              >
                <span className="grid size-7 place-items-center rounded-md bg-ink font-mono text-xs font-bold text-signal">
                  {index + 1}
                </span>
                <span className="mt-4 font-semibold text-ink">{step.title}</span>
                <span className="mt-1 flex-1 text-sm leading-6 text-muted">{step.body}</span>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-petrol">
                  Open <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <p className="text-xs text-muted">Gmail drafts are not counted yet.</p>
    </div>
  );
}
