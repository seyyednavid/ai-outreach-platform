
import { useState } from "react";
import {
  CheckCircle2,
  Pencil,
  Save,
  X,
} from "lucide-react";

import {
  approveEmailDraft,
  saveEmailDraft,
  type EmailDraft,
  type OutreachRun,
} from "../api/outreach";

interface EmailEditorProps {
  run: OutreachRun;
  onUpdate: (updated: OutreachRun) => void;
}

export default function EmailEditor({
  run,
  onUpdate,
}: EmailEditorProps) {
  const currentEmail = run.final_email ?? run.email;

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<EmailDraft>({
    ...currentEmail,
  });

  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const busy = saving || approving;

  const hasChanges =
    draft.subject !== currentEmail.subject ||
    draft.body !== currentEmail.body ||
    draft.call_to_action !== currentEmail.call_to_action;

  function updateField(field: keyof EmailDraft, value: string) {
    setDraft((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function startEditing() {
    setDraft({ ...currentEmail });
    setError(null);
    setEditing(true);
  }

  function cancelEditing() {
    setDraft({ ...currentEmail });
    setError(null);
    setEditing(false);
  }

  async function handleSave() {
    if (
      !draft.subject.trim() ||
      !draft.body.trim() ||
      !draft.call_to_action.trim()
    ) {
      setError("Please complete all email fields.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const updated = await saveEmailDraft(run.id, draft);
      onUpdate(updated);
      setEditing(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save email",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove() {
    if (
      !window.confirm(
        "Have you reviewed the email and verified its claims?",
      )
    ) {
      return;
    }

    setApproving(true);
    setError(null);

    try {
      const updated = await approveEmailDraft(run.id);
      onUpdate(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to approve email",
      );
    } finally {
      setApproving(false);
    }
  }

  const inputClass =
    "w-full rounded-xl border border-slate-200 bg-white " +
    "px-4 py-3 text-sm outline-none focus:border-indigo-500 " +
    "focus:ring-2 focus:ring-indigo-100";

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-lg font-semibold">Email Draft</h3>

        {run.human_approved ? (
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
            Human Approved
          </span>
        ) : (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
            Awaiting Human Approval
          </span>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {editing ? (
        <div className="mt-5 space-y-4">
          <label className="block space-y-2 text-sm font-medium">
            Subject
            <input
              className={inputClass}
              value={draft.subject}
              disabled={busy}
              onChange={(e) => updateField("subject", e.target.value)}
            />
          </label>

          <label className="block space-y-2 text-sm font-medium">
            Email Body
            <textarea
              className={inputClass}
              rows={12}
              value={draft.body}
              disabled={busy}
              onChange={(e) => updateField("body", e.target.value)}
            />
          </label>

          <label className="block space-y-2 text-sm font-medium">
            Call to Action
            <textarea
              className={inputClass}
              rows={2}
              value={draft.call_to_action}
              disabled={busy}
              onChange={(e) =>
                updateField("call_to_action", e.target.value)
              }
            />
          </label>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleSave()}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Save size={17} />
              {saving ? "Saving..." : "Save Changes"}
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={cancelEditing}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm"
            >
              <X size={17} />
              Cancel
            </button>
          </div>

          {hasChanges && run.human_approved && (
            <p className="text-sm text-amber-700">
              Saving these edits will reset the previous approval.
            </p>
          )}
        </div>
      ) : (
        <>
          <p className="mt-5 text-xs font-semibold uppercase text-slate-500">
            Subject
          </p>
          <p className="mt-2 font-semibold">
            {currentEmail.subject}
          </p>

          <div className="mt-5 whitespace-pre-wrap rounded-xl bg-slate-50 p-5 text-sm leading-7">
            {currentEmail.body}
          </div>

          <p className="mt-4 text-sm text-slate-600">
            <strong>CTA:</strong> {currentEmail.call_to_action}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={startEditing}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50"
            >
              <Pencil size={17} />
              Edit Email
            </button>

            {!run.human_approved && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleApprove()}
                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <CheckCircle2 size={17} />
                {approving ? "Approving..." : "Approve Email"}
              </button>
            )}
          </div>

          {run.human_approved ? (
            <p className="mt-4 text-sm text-emerald-700">
              Approved on{" "}
              {run.approved_at
                ? new Date(run.approved_at).toLocaleString()
                : "an unknown date"}
            </p>
          ) : (
            <p className="mt-4 text-sm text-amber-700">
              Review the email and verify its claims before approving.
            </p>
          )}
        </>
      )}
    </section>
  );
}
