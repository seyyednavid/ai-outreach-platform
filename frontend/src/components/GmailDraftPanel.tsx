
import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  LoaderCircle,
  MailPlus,
  RefreshCw,
} from "lucide-react";

import {
  createGmailDraft,
  getGmailStatus,
  GMAIL_CONNECT_URL,
} from "../api/gmail";
import type { OutreachRun } from "../api/outreach";

interface GmailDraftPanelProps {
  run: OutreachRun;
  recipientEmail?: string | null;
}

export default function GmailDraftPanel({
  run,
  recipientEmail,
}: GmailDraftPanelProps) {
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(true);
  const [creating, setCreating] = useState(false);

  const [email, setEmail] = useState(
    recipientEmail ?? "",
  );

  const [draftId, setDraftId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getGmailStatus()
      .then((result) => {
        if (!cancelled) {
          setConnected(result.connected);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to check Gmail connection",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setChecking(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshStatus() {
    setChecking(true);
    setError(null);

    try {
      const result = await getGmailStatus();
      setConnected(result.connected);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to check Gmail connection",
      );
    } finally {
      setChecking(false);
    }
  }

  async function handleCreateDraft() {
    if (
      !run.human_approved ||
      !connected ||
      !email.trim() ||
      creating
    ) {
      return;
    }

    const confirmed = window.confirm(
      `Create a Gmail draft for ${email.trim()}?\n\n` +
      "The email will NOT be sent.",
    );

    if (!confirmed) return;

    setCreating(true);
    setError(null);
    setDraftId(null);

    try {
      const result = await createGmailDraft(
        run.id,
        email.trim(),
      );

      setDraftId(result.draft_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to create Gmail draft",
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">
            Gmail Integration
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            Create a Gmail draft from your approved email.
          </p>
        </div>

        {checking ? (
          <span className="text-sm text-slate-500">
            Checking...
          </span>
        ) : connected ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
            <CheckCircle2 size={14} />
            Gmail Connected
          </span>
        ) : (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
            Gmail Not Connected
          </span>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700"
        >
          <AlertCircle size={18} className="shrink-0" />
          {error}
        </div>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        {!checking && !connected && (
          <a
            href={GMAIL_CONNECT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
          >
            Connect Gmail
            <ExternalLink size={16} />
          </a>
        )}

        <button
          type="button"
          onClick={() => void refreshStatus()}
          disabled={checking || creating}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={16} />
          Refresh Status
        </button>
      </div>

      <div className="mt-5">
        <label
          htmlFor="gmail-recipient"
          className="block text-sm font-medium"
        >
          Recipient Email
        </label>

        <input
          id="gmail-recipient"
          type="email"
          value={email}
          disabled={creating}
          placeholder="recipient@example.com"
          onChange={(event) => {
            setEmail(event.target.value);
            setDraftId(null);
          }}
          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      {!run.human_approved && (
        <div className="mt-4 flex gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          <AlertCircle
            size={18}
            className="shrink-0"
          />
          Human approval is required before creating a draft.
        </div>
      )}

      <button
        type="button"
        disabled={
          !run.human_approved ||
          !connected ||
          !email.trim() ||
          checking ||
          creating
        }
        onClick={() => void handleCreateDraft()}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {creating ? (
          <LoaderCircle
            size={18}
            className="animate-spin"
          />
        ) : (
          <MailPlus size={18} />
        )}

        {creating
          ? "Creating Gmail Draft..."
          : "Create Gmail Draft"}
      </button>

      {draftId && (
        <div
          role="status"
          className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm"
        >
          <p className="flex items-center gap-2 font-semibold text-emerald-800">
            <CheckCircle2 size={18} />
            Gmail draft created successfully!
          </p>

          <p className="mt-2 break-all text-xs text-emerald-700">
            Draft ID: {draftId}
          </p>

          <a
            href="https://mail.google.com/mail/u/0/#drafts"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-2 font-medium text-indigo-700 hover:underline"
          >
            Open Gmail Drafts
            <ExternalLink size={16} />
          </a>
        </div>
      )}

      <p className="mt-4 text-xs text-slate-500">
        Drafts are saved in Gmail and are never sent automatically.
        Creating again will make another draft.
      </p>
    </section>
  );
}
