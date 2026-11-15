import { useRef, useState } from "react";
import { CheckCircle2, ExternalLink, Search, UserCheck, UserX, Users } from "lucide-react";

import {
  discoverContacts,
  type ContactDiscoveryResponse,
  type ReviewedContact,
} from "../api/contacts";
import { Badge, Button, Card, CardHeader, Notice, type Tone } from "./ui";
import { getErrorMessage } from "./ui-classes";

interface Props {
  step: number;
  leadId: number | null;
  onSelectContact?: (contact: ReviewedContact | null) => void;
}

const evidence: Record<string, { label: string; tone: Tone }> = {
  VERIFIED: { label: "Source checked", tone: "ok" },
  EXCERPT_CONSISTENT: { label: "Excerpt only", tone: "warn" },
  NEEDS_REVIEW: { label: "Needs review", tone: "warn" },
  REJECTED: { label: "Rejected", tone: "bad" },
};

function contactKey(contact: ReviewedContact): string {
  return [contact.name, contact.company_name, contact.job_title]
    .map((part) => part.trim().toLowerCase())
    .join("|");
}

export default function ContactDiscoveryPanel({ step, leadId, onSelectContact }: Props) {
  const [result, setResult] = useState<ContactDiscoveryResponse | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ignore a previous request if a new search starts.
  const requestIdRef = useRef(0);

  async function handleDiscover() {
    if (leadId === null || discovering) return;
    const requestId = ++requestIdRef.current;

    setDiscovering(true);
    setResult(null);
    setSelectedKey(null);
    setError(null);
    onSelectContact?.(null);

    try {
      const response = await discoverContacts(leadId);
      if (requestId !== requestIdRef.current) return;
      setResult(response);
    } catch (err: unknown) {
      if (requestId !== requestIdRef.current) return;
      setError(getErrorMessage(err, "Contact search failed. Try again."));
    } finally {
      if (requestId === requestIdRef.current) setDiscovering(false);
    }
  }

  function handleSelect(contact: ReviewedContact) {
    if (contact.evidence_status === "REJECTED") return;
    const key = contactKey(contact);
    if (selectedKey === key) {
      clearSelection();
      return;
    }
    setSelectedKey(key);
    onSelectContact?.(contact);
  }

  function clearSelection() {
    setSelectedKey(null);
    onSelectContact?.(null);
  }

  return (
    <Card className="p-5 md:p-6">
      <CardHeader
        step={step}
        title="Choose a contact"
        tag={<Badge>Optional</Badge>}
        description="Searches public sources for people in the lead's target role. Job titles and employers may be out of date."
        actions={
          selectedKey && (
            <Button variant="ghost" size="sm" icon={UserX} onClick={clearSelection}>
              Continue without contact
            </Button>
          )
        }
      />

      <div className="mt-5">
        <Button
          variant={result ? "secondary" : "primary"}
          icon={Search}
          loading={discovering}
          disabled={leadId === null || discovering}
          onClick={() => void handleDiscover()}
        >
          {discovering ? "Searching public sources…" : result ? "Search again" : "Find contacts"}
        </Button>
      </div>

      {error && (
        <div className="mt-4">
          <Notice tone="bad">{error}</Notice>
        </div>
      )}

      {result && (
        <div className="mt-5 space-y-3">
          <p className="text-sm leading-6 text-ink-soft">{result.search_summary}</p>

          {result.contacts.length === 0 ? (
            <p className="rounded-md border border-dashed border-line-strong p-6 text-center text-sm text-muted">
              No suitable contacts were found. The email will use a neutral greeting.
            </p>
          ) : (
            <ul className="space-y-3">
              {result.contacts.map((contact, index) => {
                const key = contactKey(contact);
                const isSelected = selectedKey === key;
                const isRejected = contact.evidence_status === "REJECTED";
                const status = evidence[contact.evidence_status] ?? {
                  label: contact.evidence_status,
                  tone: "neutral" as Tone,
                };

                return (
                  <li
                    key={`${key}-${index}`}
                    className={`rounded-md border p-4 transition-colors ${
                      isSelected
                        ? "border-petrol bg-petrol-wash/50 ring-1 ring-petrol"
                        : "border-line"
                    } ${isRejected ? "opacity-70" : ""}`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-ink">{contact.name}</p>
                        <p className="text-sm text-ink-soft">
                          {contact.job_title} · {contact.company_name}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="font-mono text-xs text-muted"
                          title="Role relevance, scored by keyword match"
                        >
                          fit {contact.relevance_score}
                        </span>
                        <Badge tone={status.tone}>{status.label}</Badge>
                      </div>
                    </div>

                    <p className="mt-3 text-sm leading-6 text-ink-soft">{contact.relevance_reason}</p>

                    <blockquote className="mt-3 border-l-2 border-line-strong pl-3 text-[13px] leading-5 text-muted">
                      “{contact.source_excerpt}”
                      <a
                        href={contact.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-1.5 inline-flex items-center gap-1 font-medium text-petrol hover:underline"
                      >
                        Source <ExternalLink size={12} />
                      </a>
                    </blockquote>

                    {contact.evidence_warnings.length > 0 && (
                      <ul className="mt-3 space-y-1 text-xs leading-5 text-warn">
                        {contact.evidence_warnings.map((warning, warningIndex) => (
                          <li key={warningIndex}>— {warning}</li>
                        ))}
                      </ul>
                    )}

                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-muted">
                        <span className="font-medium text-ink-soft">Work email:</span>{" "}
                        {contact.public_work_email ?? "not published or not confirmed"}
                      </p>
                      <Button
                        size="sm"
                        variant={isSelected ? "primary" : "secondary"}
                        icon={isSelected ? CheckCircle2 : UserCheck}
                        disabled={isRejected}
                        onClick={() => handleSelect(contact)}
                        aria-pressed={isSelected}
                      >
                        {isRejected ? "Can't be used" : isSelected ? "Selected" : "Use this contact"}
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {result.limitations.length > 0 && (
            <details className="rounded-md border border-line px-4 py-3 text-sm">
              <summary className="cursor-pointer font-medium text-ink-soft">
                Search limitations ({result.limitations.length})
              </summary>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-[13px] leading-5 text-muted">
                {result.limitations.map((limitation, index) => (
                  <li key={index}>{limitation}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {!result && !discovering && (
        <p className="mt-3 flex items-center gap-2 text-xs text-muted">
          <Users size={14} />
          Skip this step and the email will open with a neutral greeting.
        </p>
      )}
      <p className="sr-only" aria-live="polite">
        {result ? `${result.contacts.length} contacts found` : ""}
      </p>
    </Card>
  );
}
