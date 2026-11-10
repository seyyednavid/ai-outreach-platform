
import { useEffect, useState, type FormEvent } from "react";
import { Building2, Plus, RefreshCw } from "lucide-react";

import {
  createLead,
  getLeads,
  type Lead,
  type LeadCreate,
} from "../api/leads";

const emptyForm: LeadCreate = {
  company_name: "",
  website: null,
  industry: "",
  target_role: "",
  pain_point: "",
  recipient_name: null,
  recipient_email: null,
};

const inputClass =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 " +
  "text-sm outline-none focus:border-indigo-500 focus:ring-2 " +
  "focus:ring-indigo-100";

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [form, setForm] = useState<LeadCreate>({ ...emptyForm });
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadLeads() {
    setLoading(true);
    setError(null);

    try {
      const data = await getLeads();
      setLeads(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load leads",
      );
    } finally {
      setLoading(false);
    }
  }

  
useEffect(() => {
  let cancelled = false;

  getLeads()
    .then((data) => {
      if (!cancelled) {
        setLeads(data);
      }
    })
    .catch((err: unknown) => {
      if (!cancelled) {
        setError(
          err instanceof Error ? err.message : "Failed to load leads"
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


  function updateField(
    field: keyof LeadCreate,
    value: string,
  ) {
    setForm((current) => ({
      ...current,
      [field]: value || null,
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const created = await createLead(form);
      setLeads((current) => [created, ...current]);
      setForm({ ...emptyForm });
      setShowForm(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create lead",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold">Leads</h2>
          <p className="mt-2 text-slate-500">
            Manage companies and contacts for AI outreach.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void loadLeads()}
            disabled={loading}
            className="rounded-lg border border-slate-200 bg-white p-3 hover:bg-slate-100 disabled:opacity-50"
            aria-label="Refresh leads"
          >
            <RefreshCw size={18} />
          </button>

          <button
            type="button"
            onClick={() => setShowForm((current) => !current)}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus size={18} />
            {showForm ? "Close form" : "Add Lead"}
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={(event) => void handleSubmit(event)}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h3 className="mb-5 text-lg font-semibold">New Lead</h3>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm font-medium">
              Company Name *
              <input
                className={inputClass}
                value={form.company_name}
                onChange={(e) => updateField("company_name", e.target.value)}
                required
              />
            </label>

            <label className="space-y-1 text-sm font-medium">
              Website
              <input
                className={inputClass}
                type="url"
                value={form.website ?? ""}
                onChange={(e) => updateField("website", e.target.value)}
                placeholder="https://example.com"
              />
            </label>

            <label className="space-y-1 text-sm font-medium">
              Industry *
              <input
                className={inputClass}
                value={form.industry}
                onChange={(e) => updateField("industry", e.target.value)}
                required
              />
            </label>

            <label className="space-y-1 text-sm font-medium">
              Target Role *
              <input
                className={inputClass}
                value={form.target_role}
                onChange={(e) => updateField("target_role", e.target.value)}
                placeholder="Operations Manager"
                required
              />
            </label>

            <label className="space-y-1 text-sm font-medium">
              Recipient Name
              <input
                className={inputClass}
                value={form.recipient_name ?? ""}
                onChange={(e) => updateField("recipient_name", e.target.value)}
              />
            </label>

            <label className="space-y-1 text-sm font-medium">
              Recipient Email
              <input
                className={inputClass}
                type="email"
                value={form.recipient_email ?? ""}
                onChange={(e) => updateField("recipient_email", e.target.value)}
              />
            </label>

            <label className="space-y-1 text-sm font-medium md:col-span-2">
              Potential Pain Point *
              <textarea
                className={inputClass}
                rows={3}
                value={form.pain_point}
                onChange={(e) => updateField("pain_point", e.target.value)}
                placeholder="Describe a possible business challenge..."
                required
              />
            </label>
          </div>

          <div className="mt-5 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Lead"}
            </button>
          </div>
        </form>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h3 className="font-semibold">All Leads</h3>
          <span className="text-sm text-slate-500">
            {leads.length} records
          </span>
        </div>

        {loading ? (
          <p className="p-8 text-sm text-slate-500">Loading leads...</p>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center gap-3 p-12 text-slate-500">
            <Building2 size={32} />
            <p>No leads found. Add your first company.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-6 py-4">Company</th>
                  <th className="px-6 py-4">Industry</th>
                  <th className="px-6 py-4">Target Role</th>
                  <th className="px-6 py-4">Contact</th>
                  <th className="px-6 py-4">ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      <p className="font-semibold">{lead.company_name}</p>
                      {lead.website && (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-600 hover:underline"
                        >
                          {lead.website}
                        </a>
                      )}
                    </td>
                    <td className="px-6 py-4">{lead.industry}</td>
                    <td className="px-6 py-4">{lead.target_role}</td>
                    <td className="px-6 py-4">
                      {lead.recipient_name || lead.recipient_email || "—"}
                    </td>
                    <td className="px-6 py-4 text-slate-500">#{lead.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
