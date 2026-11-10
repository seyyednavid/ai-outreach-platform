
import { useEffect, useState } from "react";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  ChartNoAxesColumn,
  RefreshCw,
  Workflow,
} from "lucide-react";

import {
  getDashboardStats,
  type DashboardStats,
} from "../api/dashboard";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getDashboardStats()
      .then((data) => {
        if (!cancelled) {
          setStats(data);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load dashboard",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshStats() {
    setLoading(true);
    setError(null);

    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to refresh dashboard",
      );
    } finally {
      setLoading(false);
    }
  }

  const cards = [
    {
      title: "Total Leads",
      value: stats?.total_leads,
      description: "Companies in your database",
      icon: Building2,
      color: "text-indigo-600",
      background: "bg-indigo-50",
    },
    {
      title: "Outreach Runs",
      value: stats?.total_outreach_runs,
      description: "AI workflows executed",
      icon: Workflow,
      color: "text-blue-600",
      background: "bg-blue-50",
    },
    {
      title: "Human Approved",
      value: stats?.human_approved_emails,
      description: "Emails approved by a user",
      icon: CheckCircle2,
      color: "text-emerald-600",
      background: "bg-emerald-50",
    },
    {
      title: "Average AI Score",
      value:
        stats === null
          ? undefined
          : `${stats.average_review_score.toFixed(2)}/10`,
      description: "Average reviewer score",
      icon: ChartNoAxesColumn,
      color: "text-amber-600",
      background: "bg-amber-50",
    },
  ];

  return (
    <div className="space-y-7">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900">
            Dashboard
          </h2>

          <p className="mt-2 text-slate-500">
            Overview of your AI outreach activity.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void refreshStats()}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw
            size={17}
            className={loading ? "animate-spin" : ""}
          />
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {/* Statistics */}
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;

          return (
            <div
              key={card.title}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`rounded-xl p-3 ${card.background}`}
                >
                  <Icon
                    size={22}
                    className={card.color}
                  />
                </span>
              </div>

              <p className="mt-5 text-sm font-medium text-slate-500">
                {card.title}
              </p>

              <p className="mt-2 text-3xl font-bold text-slate-900">
                {stats === null && loading
                  ? "..."
                  : card.value ?? "—"}
              </p>

              <p className="mt-3 text-xs text-slate-400">
                {card.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Information */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold">
          Outreach Overview
        </h3>

        <p className="mt-3 text-sm leading-7 text-slate-600">
          Manage your leads, run AI-powered outreach
          workflows, review generated emails and create
          Gmail drafts after human approval.
        </p>

        <p className="mt-3 text-xs text-slate-400">
          Statistics are calculated from PostgreSQL.
          Gmail draft counts are not tracked yet.
        </p>
      </section>
    </div>
  );
}
