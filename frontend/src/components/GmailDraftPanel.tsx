import { useEffect, useState } from "react";
import { ExternalLink, Link2, MailPlus, RefreshCw, Send } from "lucide-react";

import { createGmailDraft, getGmailConnectUrl, getGmailStatus } from "../api/gmail";
import type { OutreachRun } from "../api/outreach";
import { Badge, Button, Card, CardHeader, Field, Notice } from "./ui";
import { getErrorMessage, inputClass } from "./ui-classes";

interface GmailDraftPanelProps {
  run: OutreachRun;
  recipientEmail?: string | null;
}

export default function GmailDraftPanel({ run, recipientEmail }: GmailDraftPanelProps) {
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(true);
  const [creating, setCreating] = useState(false);
  const [email, setEmail] = useState(recipientEmail ?? "");
  const [draftId, setDraftId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getGmailStatus()
      .then((result) => {
        if (!cancelled) setConnected(result.connected);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not check the Gmail connection."));
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
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
      setError(getErrorMessage(err, "Could not check the Gmail connection."));
    } finally {
      setChecking(false);
    }
  }

  async function handleConnect() {
    // Open the tab now, inside the click, so pop-up blockers allow it.
    const tab = window.open("", "_blank");
    if (tab) tab.opener = null;
    setError(null);
    try {
      const url = await getGmailConnectUrl();
      if (tab) tab.location.href = url;
      else window.location.href = url;
    } catch (err) {
      tab?.close();
      setError(getErrorMessage(err, "Could not start the Gmail connection."));
    }
  }

  async function handleCreateDraft() {
    const recipient = email.trim();
    if (!run.human_approved || !connected || !recipient || creating) return;

    if (!window.confirm(`Create a Gmail draft addressed to ${recipient}?\n\nIt will not be sent.`)) {
      return;
    }

    setCreating(true);
    setError(null);
    setDraftId(null);
    try {
      const result = await createGmailDraft(run.id, recipient);
      setDraftId(result.draft_id);
    } catch (err) {
      setError(getErrorMessage(err, "The Gmail draft could not be created."));
    } finally {
      setCreating(false);
    }
  }

  const ready = run.human_approved && connected && email.trim() !== "";

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        icon={Send}
        title="Save to Gmail"
        description="Creates a draft in your Gmail. You send it yourself."
        tag={
          checking ? (
            <Badge>Checking…</Badge>
          ) : connected ? (
            <Badge tone="ok">Connected</Badge>
          ) : (
            <Badge tone="warn">Not connected</Badge>
          )
        }
        actions={
          <Button
            variant="ghost"
            size="sm"
            icon={RefreshCw}
            disabled={checking || creating}
            onClick={() => void refreshStatus()}
            aria-label="Check Gmail connection again"
          >
            Recheck
          </Button>
        }
      />

      <div className="mt-5 space-y-4">
        {error && <Notice tone="bad">{error}</Notice>}

        {!checking && !connected && (
          <Notice tone="warn">
            Connect your Gmail in a new tab, then press Recheck.
            <div className="mt-2">
              <Button variant="secondary" size="sm" icon={Link2} onClick={() => void handleConnect()}>
                Connect Gmail
              </Button>
            </div>
          </Notice>
        )}

        {!run.human_approved && (
          <Notice tone="neutral">Approve the email above to unlock this step.</Notice>
        )}

        <Field label="Recipient" hint="Use an address you have confirmed yourself">
          <input
            type="email"
            className={inputClass}
            value={email}
            disabled={creating}
            placeholder="name@company.com"
            onChange={(event) => {
              setEmail(event.target.value);
              setDraftId(null);
            }}
          />
        </Field>

        <Button
          icon={MailPlus}
          loading={creating}
          disabled={!ready || checking || creating}
          onClick={() => void handleCreateDraft()}
          className="w-full sm:w-auto"
        >
          {creating ? "Creating draft…" : "Create Gmail draft"}
        </Button>

        {draftId && (
          <Notice tone="ok" title="Draft created in Gmail" role="status">
            <a
              href="https://mail.google.com/mail/u/0/#drafts"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-semibold underline underline-offset-2"
            >
              Open Gmail drafts <ExternalLink size={13} />
            </a>
            <span className="ml-2 font-mono text-xs opacity-70">{draftId}</span>
          </Notice>
        )}

        <p className="text-xs text-muted">
          Each click creates a new draft. Nothing is sent automatically.
        </p>
      </div>
    </Card>
  );
}
