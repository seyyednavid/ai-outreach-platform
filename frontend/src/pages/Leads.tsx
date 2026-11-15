import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Building2, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";

import {
  createLead,
  deleteLead,
  getLeads,
  updateLead,
  type Lead,
  type LeadCreate,
} from "../api/leads";
import { Button, Card, CardHeader, EmptyState, Field, Notice, PageHeader } from "../components/ui";
import { getErrorMessage, inputClass } from "../components/ui-classes";

const emptyForm: LeadCreate = {
  company_name: "",
  website: null,
  industry: "",
  target_role: "",
  pain_point: "",
  recipient_name: null,
  recipient_email: null,
};

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [form, setForm] = useState<LeadCreate>({ ...emptyForm });
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getLeads()
      .then((data) => {
        if (!cancelled) setLeads(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load leads."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadLeads() {
    setLoading(true);
    setError(null);
    try {
      setLeads(await getLeads());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load leads."));
    } finally {
      setLoading(false);
    }
  }

  function updateField(field: keyof LeadCreate, value: string) {
    setForm((current) => ({ ...current, [field]: value || null }));
  }

  function openNewForm() {
    setEditingId(null);
    setForm({ ...emptyForm });
    setShowForm(true);
    setError(null);
  }

  function openEditForm(lead: Lead) {
    setEditingId(lead.id);
    setForm({
      company_name: lead.company_name,
      website: lead.website,
      industry: lead.industry,
      target_role: lead.target_role,
      pain_point: lead.pain_point,
      recipient_name: lead.recipient_name,
      recipient_email: lead.recipient_email,
    });
    setShowForm(true);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm({ ...emptyForm });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (editingId !== null) {
        const updated = await updateLead(editingId, form);
        setLeads((current) => current.map((lead) => (lead.id === updated.id ? updated : lead)));
      } else {
        const created = await createLead(form);
        setLeads((current) => [created, ...current]);
      }
      closeForm();
    } catch (err) {
      setError(getErrorMessage(err, "The lead could not be saved."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(lead: Lead) {
    const drafts =
      lead.run_count > 0
        ? `\n\nIts ${lead.run_count} draft${lead.run_count === 1 ? "" : "s"} will be deleted too.`
        : "";
    if (!window.confirm(`Delete "${lead.company_name}"?${drafts}\n\nThis cannot be undone.`)) {
      return;
    }

    setDeletingId(lead.id);
    setError(null);
    try {
      await deleteLead(lead.id);
      setLeads((current) => current.filter((item) => item.id !== lead.id));
      if (editingId === lead.id) closeForm();
    } catch (err) {
      setError(getErrorMessage(err, "The lead could not be deleted."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Leads"
        description="Companies you want to reach, and what you think they might need."
        actions={
          <>
            <Button
              variant="secondary"
              icon={RefreshCw}
              disabled={loading}
              onClick={() => void loadLeads()}
              aria-label="Reload leads"
            />
            <Button
              variant={showForm ? "secondary" : "primary"}
              icon={showForm ? X : Plus}
              onClick={() => (showForm ? closeForm() : openNewForm())}
            >
              {showForm ? "Close" : "Add lead"}
            </Button>
          </>
        }
      />

      {error && <Notice tone="bad">{error}</Notice>}

      {showForm && (
        <Card as="div" className="p-5 md:p-6">
          <form onSubmit={(event) => void handleSubmit(event)}>
            <CardHeader
              title={editingId !== null ? `Edit ${form.company_name || "lead"}` : "New lead"}
              description={
                editingId !== null
                  ? "Changes apply to new drafts and AI checks. Existing drafts keep their text."
                  : "Fields marked * are required."
              }
            />

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <Field label="Company name *">
                <input
                  className={inputClass}
                  value={form.company_name}
                  onChange={(e) => updateField("company_name", e.target.value)}
                  required
                />
              </Field>
              <Field label="Website">
                <input
                  className={inputClass}
                  type="url"
                  value={form.website ?? ""}
                  onChange={(e) => updateField("website", e.target.value)}
                  placeholder="https://example.com"
                />
              </Field>
              <Field label="Industry *">
                <input
                  className={inputClass}
                  value={form.industry}
                  onChange={(e) => updateField("industry", e.target.value)}
                  placeholder="Retail"
                  required
                />
              </Field>
              <Field label="Role to reach *">
                <input
                  className={inputClass}
                  value={form.target_role}
                  onChange={(e) => updateField("target_role", e.target.value)}
                  placeholder="Head of Store Operations"
                  required
                />
              </Field>
              <Field label="Contact name">
                <input
                  className={inputClass}
                  value={form.recipient_name ?? ""}
                  onChange={(e) => updateField("recipient_name", e.target.value)}
                />
              </Field>
              <Field label="Contact email" hint="Pre-fills the Gmail recipient">
                <input
                  className={inputClass}
                  type="email"
                  value={form.recipient_email ?? ""}
                  onChange={(e) => updateField("recipient_email", e.target.value)}
                />
              </Field>
              <Field
                label="Possible need *"
                hint="Treated as unconfirmed by every agent"
                className="md:col-span-2"
              >
                <textarea
                  className={`${inputClass} leading-6`}
                  rows={3}
                  value={form.pain_point}
                  onChange={(e) => updateField("pain_point", e.target.value)}
                  placeholder="Long queues at service counters during peak hours"
                  required
                />
              </Field>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={closeForm}>
                Cancel
              </Button>
              <Button type="submit" loading={saving} disabled={saving}>
                {saving ? "Saving…" : editingId !== null ? "Save changes" : "Save lead"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="font-semibold">All leads</h2>
          <span className="font-mono text-xs text-muted">{leads.length} total</span>
        </div>

        {loading ? (
          <p className="p-6 text-sm text-muted">Loading leads…</p>
        ) : leads.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Building2}
              title="No leads yet"
              action={
                <Button icon={Plus} onClick={openNewForm}>
                  Add your first lead
                </Button>
              }
            >
              Add a company you want to reach. You can then write a draft for it on the New draft page.
            </EmptyState>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-paper/60">
                  {["Company", "Industry", "Role to reach", "Contact", "Drafts", ""].map((heading) => (
                    <th
                      key={heading}
                      scope="col"
                      className="px-5 py-2.5 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-muted"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {leads.map((lead) => (
                  <tr key={lead.id} className="align-top hover:bg-paper/50">
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-ink">{lead.company_name}</p>
                      {lead.website && (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-petrol hover:underline"
                        >
                          {lead.website.replace(/^https?:\/\//, "")}
                        </a>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-ink-soft">{lead.industry}</td>
                    <td className="px-5 py-3.5 text-ink-soft">{lead.target_role}</td>
                    <td className="px-5 py-3.5 text-ink-soft">
                      {lead.recipient_name || lead.recipient_email || <span className="text-muted">—</span>}
                    </td>
                    <td className="px-5 py-3.5">
                      {lead.run_count > 0 ? (
                        <Link
                          to={`/drafts?lead=${lead.id}`}
                          className="font-mono text-xs font-semibold text-petrol hover:underline"
                        >
                          {lead.run_count} →
                        </Link>
                      ) : (
                        <span className="font-mono text-xs text-muted">0</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1.5">
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={Pencil}
                          disabled={deletingId !== null}
                          onClick={() => openEditForm(lead)}
                          aria-label={`Edit ${lead.company_name}`}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          icon={Trash2}
                          loading={deletingId === lead.id}
                          disabled={deletingId !== null}
                          onClick={() => void handleDelete(lead)}
                          aria-label={`Delete ${lead.company_name}`}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
