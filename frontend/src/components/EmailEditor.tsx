import { useState } from "react";
import { CheckCircle2, Mail, Pencil, Save, ShieldCheck, X } from "lucide-react";

import {
  approveEmailDraft,
  recheckEmailDraft,
  saveEmailDraft,
  type EmailDraft,
  type OutreachRun,
} from "../api/outreach";
import { editsUnchecked } from "./run-status";
import { Badge, Button, Card, CardHeader, Field, Label, Notice } from "./ui";
import { getErrorMessage, inputClass } from "./ui-classes";

interface EmailEditorProps {
  run: OutreachRun;
  onUpdate: (updated: OutreachRun) => void;
}

export default function EmailEditor({ run, onUpdate }: EmailEditorProps) {
  const currentEmail = run.final_email ?? run.email;

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<EmailDraft>({ ...currentEmail });
  const [checked, setChecked] = useState(false);
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const busy = saving || approving || checking;
  // Approval follows the latest review: of your edits once checked.
  const reviewFailed = !run.review_passed;
  const unchecked = editsUnchecked(run);

  const hasChanges =
    draft.subject !== currentEmail.subject ||
    draft.body !== currentEmail.body ||
    draft.call_to_action !== currentEmail.call_to_action;

  function updateField(field: keyof EmailDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
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
    if (!draft.subject.trim() || !draft.body.trim() || !draft.call_to_action.trim()) {
      setError("Fill in the subject, body and call to action before saving.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await saveEmailDraft(run.id, draft);
      onUpdate(updated);
      setEditing(false);
      setChecked(false);
    } catch (err) {
      setError(getErrorMessage(err, "The email could not be saved."));
    } finally {
      setSaving(false);
    }
  }

  async function handleRecheck() {
    setChecking(true);
    setError(null);
    try {
      const updated = await recheckEmailDraft(run.id);
      onUpdate(updated);
      setChecked(false);
    } catch (err) {
      setError(getErrorMessage(err, "The AI check failed. Your email is unchanged — try again."));
    } finally {
      setChecking(false);
    }
  }

  async function handleApprove() {
    if (!checked) return;

    setApproving(true);
    setError(null);
    try {
      const updated = await approveEmailDraft(run.id, reviewFailed);
      onUpdate(updated);
    } catch (err) {
      setError(getErrorMessage(err, "The email could not be approved."));
    } finally {
      setApproving(false);
    }
  }

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        icon={Mail}
        title="Email draft"
        tag={run.final_email ? <Badge tone="accent">Edited by you</Badge> : undefined}
        actions={
          !editing && (
            <Button variant="secondary" size="sm" icon={Pencil} disabled={busy} onClick={startEditing}>
              Edit
            </Button>
          )
        }
      />

      {error && (
        <div className="mt-4">
          <Notice tone="bad">{error}</Notice>
        </div>
      )}

      {editing ? (
        <div className="mt-5 space-y-4">
          <Field label="Subject">
            <input
              className={inputClass}
              value={draft.subject}
              disabled={busy}
              onChange={(e) => updateField("subject", e.target.value)}
            />
          </Field>
          <Field label="Body">
            <textarea
              className={`${inputClass} leading-6`}
              rows={12}
              value={draft.body}
              disabled={busy}
              onChange={(e) => updateField("body", e.target.value)}
            />
          </Field>
          <Field label="Call to action" hint="Recorded with the draft; not added to the Gmail body">
            <textarea
              className={inputClass}
              rows={2}
              value={draft.call_to_action}
              disabled={busy}
              onChange={(e) => updateField("call_to_action", e.target.value)}
            />
          </Field>

          {hasChanges && run.human_approved && (
            <Notice tone="warn">Saving will remove your earlier approval.</Notice>
          )}

          <div className="flex flex-wrap gap-2">
            <Button icon={Save} loading={saving} disabled={busy} onClick={() => void handleSave()}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
            <Button variant="ghost" icon={X} disabled={busy} onClick={cancelEditing}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          {/* Rendered like the message the recipient will see */}
          <div className="mt-5 overflow-hidden rounded-md border border-line">
            <div className="border-b border-line bg-paper/60 px-4 py-3">
              <Label>Subject</Label>
              <p className="mt-1 font-semibold text-ink">{currentEmail.subject}</p>
            </div>
            <div className="whitespace-pre-wrap px-4 py-4 text-[15px] leading-7 text-ink">
              {currentEmail.body}
            </div>
          </div>
          <p className="mt-3 text-sm text-muted">
            <span className="font-medium text-ink-soft">Call to action:</span>{" "}
            {currentEmail.call_to_action}
          </p>

          {/* Approval */}
          <div className="mt-6 border-t border-line pt-5">
            {run.human_approved ? (
              <Notice tone={run.review_override ? "warn" : "ok"} role="status">
                {run.review_override ? "Approved with override" : "Approved"} on{" "}
                {run.approved_at ? new Date(run.approved_at).toLocaleString() : "an unknown date"}.
                Editing the email removes the approval.
              </Notice>
            ) : (
              <div className="space-y-4">
                {unchecked && (
                  <div className="rounded-md border border-petrol/30 bg-petrol-wash/50 p-4">
                    <p className="text-sm font-semibold text-ink">Check your edits with the AI reviewer</p>
                    <p className="mt-1 text-sm leading-6 text-ink-soft">
                      It reads your version against the same research and context as the original
                      draft. It does not change your text and takes about 10 seconds.
                    </p>
                    <Button
                      className="mt-3"
                      icon={ShieldCheck}
                      loading={checking}
                      disabled={busy}
                      onClick={() => void handleRecheck()}
                    >
                      {checking ? "Checking…" : "Check my edits with AI"}
                    </Button>
                  </div>
                )}
                {reviewFailed && (
                  <Notice
                    tone="bad"
                    title={
                      run.final_review
                        ? "Your edits failed AI review"
                        : unchecked
                          ? "The AI's draft failed review, and your edits are not checked yet"
                          : "This draft failed AI review"
                    }
                  >
                    {unchecked
                      ? "Check your edits above. If they pass, you can approve normally."
                      : "Fix the flagged claims, save, then check again. You can also approve anyway; the run will be marked as an override."}
                  </Notice>
                )}
                <label className="flex cursor-pointer items-start gap-3 text-sm leading-6 text-ink">
                  <input
                    type="checkbox"
                    className="mt-1 size-4 accent-petrol"
                    checked={checked}
                    disabled={busy}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  {reviewFailed
                    ? "I have checked every flagged claim and the email is accurate."
                    : "I have read this email and checked its claims."}
                </label>
                <Button
                  variant={reviewFailed ? "secondary" : "approve"}
                  icon={CheckCircle2}
                  loading={approving}
                  disabled={!checked || busy}
                  onClick={() => void handleApprove()}
                >
                  {approving ? "Approving…" : reviewFailed ? "Approve anyway" : "Approve email"}
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </Card>
  );
}
