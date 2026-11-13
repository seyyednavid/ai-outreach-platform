
import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  LoaderCircle,
  Mail,
  Search,
  ShieldAlert,
  Target,
  UserCheck,
  Users,
} from "lucide-react";

import {
  discoverContacts,
  type ContactDiscoveryResponse,
  type ReviewedContact,
} from "../api/contacts";

interface Props {
  leadId: number | null;
  onSelectContact?: (contact: ReviewedContact | null) => void;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Contact discovery failed";
}

function getEvidenceLabel(status: string): string {
  switch (status) {
    case "VERIFIED":
      return "Source checked";
    case "NEEDS_REVIEW":
      return "Needs Review";
    case "REJECTED":
      return "Rejected";
    case "EXCERPT_CONSISTENT":
      return "Excerpt Only";
    default:
      return status;
  }
}

function getEvidenceStyle(status: string): string {
  switch (status) {
    case "VERIFIED":
      return "bg-emerald-100 text-emerald-800";
    case "REJECTED":
      return "bg-red-100 text-red-800";
    default:
      return "bg-amber-100 text-amber-800";
  }
}

function contactKey(contact: ReviewedContact): string {
  return [
    contact.name.trim().toLowerCase(),
    contact.company_name.trim().toLowerCase(),
    contact.job_title.trim().toLowerCase(),
  ].join("|");
}

export default function ContactDiscoveryPanel({
  leadId,
  onSelectContact,
}: Props) {
  const [result, setResult] =
    useState<ContactDiscoveryResponse | null>(null);

  const [selectedKey, setSelectedKey] =
    useState<string | null>(null);

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

      setError(getErrorMessage(err));
    } finally {
      if (requestId === requestIdRef.current) {
        setDiscovering(false);
      }
    }
  }

  function handleSelect(contact: ReviewedContact) {
    if (contact.evidence_status === "REJECTED") return;

    const key = contactKey(contact);

    if (selectedKey === key) {
      setSelectedKey(null);
      onSelectContact?.(null);
      return;
    }

    setSelectedKey(key);
    onSelectContact?.(contact);
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-start gap-3">
        <div className="rounded-xl bg-indigo-100 p-3 text-indigo-600">
          <Users size={22} />
        </div>

        <div>
          <h2 className="text-lg font-semibold">
            AI Contact Discovery
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Find relevant professional contacts at your
            selected target company.
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => void handleDiscover()}
        disabled={leadId === null || discovering}
        className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {discovering ? (
          <LoaderCircle
            size={18}
            className="animate-spin"
          />
        ) : (
          <Search size={18} />
        )}

        {discovering
          ? "Discovering contacts..."
          : result
            ? "Search Again"
            : "Discover Contacts"}
      </button>

      {leadId === null && (
        <p className="mt-3 flex items-center gap-2 text-sm text-amber-700">
          <AlertCircle size={16} />
          Please select a lead first.
        </p>
      )}

      {discovering && (
        <p
          role="status"
          className="mt-3 text-sm text-indigo-600"
        >
          Searching public professional sources and
          assessing contact information. This may take a
          little while.
        </p>
      )}

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-5">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-semibold">
              Results for {result.target_company}
            </h3>

            <p className="mt-2 text-sm text-slate-600">
              {result.search_summary}
            </p>

            <p className="mt-2 text-xs text-slate-500">
              {result.contacts.length} contact
              {result.contacts.length === 1 ? "" : "s"} found
            </p>
          </div>

          {result.contacts.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center">
              <Users
                size={28}
                className="mx-auto text-slate-400"
              />

              <p className="mt-3 text-sm text-slate-600">
                No suitable contacts were found.
              </p>
            </div>
          )}

          {result.contacts.map((contact, index) => {
            const key = contactKey(contact);
            const isSelected = selectedKey === key;
            const isRejected =
              contact.evidence_status === "REJECTED";

            return (
              <article
                key={`${key}-${index}`}
                className={`rounded-xl border p-5 transition ${
                  isSelected
                    ? "border-indigo-400 bg-indigo-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h4 className="font-semibold">
                      {contact.name}
                    </h4>

                    <p className="mt-1 text-sm text-slate-600">
                      {contact.job_title}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {contact.company_name}
                    </p>
                  </div>

                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${getEvidenceStyle(
                      contact.evidence_status,
                    )}`}
                  >
                    {getEvidenceLabel(
                      contact.evidence_status,
                    )}
                  </span>
                </div>

                <div className="mt-4 flex items-center gap-2 text-sm">
                  <Target
                    size={17}
                    className="text-indigo-600"
                  />

                  <span>
                    Role Relevance:{" "}
                    <strong>
                      {contact.relevance_score}/100
                    </strong>
                  </span>
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-indigo-500"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(0, contact.relevance_score),
                      )}%`,
                    }}
                  />
                </div>

                <div className="mt-4">
                  <p className="text-sm font-semibold">
                    Why this contact?
                  </p>

                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    {contact.relevance_reason}
                  </p>
                </div>

                <div className="mt-4 flex items-start gap-2 text-sm">
                  <Mail
                    size={17}
                    className="mt-0.5 shrink-0 text-slate-500"
                  />

                  <div>
                    <p className="font-semibold">
                      Public Work Email
                    </p>

                    <p className="mt-1 break-all text-slate-600">
                      {contact.public_work_email ??
                        "Not available or not confirmed"}
                    </p>

                    {contact.public_work_email && (
                      <p className="mt-1 text-xs text-amber-700">
                        A published address is not proof
                        that it is current or deliverable.
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 rounded-lg bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-slate-700">
                    Supporting Evidence
                  </p>

                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    {contact.source_excerpt}
                  </p>

                  <a
                    href={contact.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:underline"
                  >
                    View Source
                    <ExternalLink size={13} />
                  </a>
                </div>

                {contact.evidence_warnings.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="flex items-center gap-2 text-xs font-semibold text-amber-800">
                      <ShieldAlert size={15} />
                      Evidence Notes
                    </p>

                    <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
                      {contact.evidence_warnings.map(
                        (warning, warningIndex) => (
                          <li key={warningIndex}>
                            {warning}
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => handleSelect(contact)}
                  disabled={isRejected}
                  className={`mt-5 flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${
                    isSelected
                      ? "bg-emerald-600 text-white"
                      : "border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                  }`}
                >
                  {isSelected ? (
                    <>
                      <CheckCircle2 size={17} />
                      Selected
                    </>
                  ) : (
                    <>
                      <UserCheck size={17} />
                      Select Contact
                    </>
                  )}
                </button>
              </article>
            );
          })}

          {selectedKey && (
            <div
              role="status"
              className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-800"
            >
              Contact selected for review. No email has
              been sent or saved to Gmail.
            </div>
          )}

          {result.limitations.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
              <h4 className="flex items-center gap-2 text-sm font-semibold text-amber-900">
                <AlertCircle size={17} />
                Research Limitations
              </h4>

              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-amber-800">
                {result.limitations.map(
                  (limitation, index) => (
                    <li key={index}>
                      {limitation}
                    </li>
                  ),
                )}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
