
import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  Mail,
  Play,
} from "lucide-react";

import { getLeads, type Lead } from "../api/leads";
import {
  getLeadRuns,
  runOutreach,
  type OutreachRun,
} from "../api/outreach";

import EmailEditor from "../components/EmailEditor";
import GmailDraftPanel from "../components/GmailDraftPanel";
import SolutionMatchingPanel from "../components/SolutionMatchingPanel";
import ContactDiscoveryPanel from "../components/ContactDiscoveryPanel";
import type { ReviewedContact } from "../api/contacts";


const defaultOffering =
  "We provide queue management and customer flow solutions " +
  "for retail environments.";

const inputClass =
  "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 " +
  "text-sm outline-none focus:border-indigo-500 focus:ring-2 " +
  "focus:ring-indigo-100";

export default function Outreach() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [leadId, setLeadId] = useState("");
  const [offering, setOffering] = useState(defaultOffering);

  const [runs, setRuns] = useState<OutreachRun[]>([]);
  const [selectedRun, setSelectedRun] =
    useState<OutreachRun | null>(null);

  const [loadingLeads, setLoadingLeads] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedContact, setSelectedContact] =
  useState<ReviewedContact | null>(null);

  // Prevent old history responses from replacing a newer selection.
  const historyRequestRef = useRef(0);

  // Load leads when the page opens.
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
            err instanceof Error
              ? err.message
              : "Failed to load leads",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingLeads(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Load outreach history for the selected lead.
  async function handleLeadChange(value: string) {
    const requestId = ++historyRequestRef.current;

    setLeadId(value);
    setSelectedContact(null);
    setRuns([]);
    setSelectedRun(null);
    setError(null);

    if (!value) {
      setLoadingHistory(false);
      return;
    }

    setLoadingHistory(true);

    try {
      const data = await getLeadRuns(Number(value));

      if (requestId !== historyRequestRef.current) {
        return;
      }

      setRuns(data);
      setSelectedRun(data[0] ?? null);
    } catch (err) {
      if (requestId !== historyRequestRef.current) {
        return;
      }

      setError(
        err instanceof Error
          ? err.message
          : "Failed to load history",
      );
    } finally {
      if (requestId === historyRequestRef.current) {
        setLoadingHistory(false);
      }
    }
  }

  // Run the existing Research -> Write -> Review -> Improve workflow.
  async function handleRun() {
    if (!leadId || offering.trim().length < 10 || running) {
      return;
    }

    const currentLeadId = Number(leadId);

    setRunning(true);
    setError(null);

    try {
      const result = await runOutreach(
        currentLeadId,
        offering.trim(),
      );

      setRuns((current) => [result, ...current]);
      setSelectedRun(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Workflow failed",
      );
    } finally {
      setRunning(false);
    }
  }

  // Called by EmailEditor after saving or approving an email.
  function handleRunUpdate(updated: OutreachRun) {
    setSelectedRun(updated);

    setRuns((current) =>
      current.map((run) =>
        run.id === updated.id ? updated : run,
      ),
    );
  }

  const selectedLeadId = leadId ? Number(leadId) : null;

  return (
    <div className="space-y-7">
      {/* Page Header */}
      <div>
        <h2 className="text-3xl font-bold">
          Outreach Workspace
        </h2>

        <p className="mt-2 text-slate-500">
          Research companies, match products, discover contacts,
          generate emails, and review AI results.
        </p>
      </div>

      {/* General Errors */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {/* Step 1: Select Lead */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-5 text-lg font-semibold">
          Step 1 — Select Target Lead
        </h3>

        <label className="block space-y-2 text-sm font-medium">
          Select Lead

          <select
            className={inputClass}
            value={leadId}
            disabled={loadingLeads || running}
            onChange={(event) =>
              void handleLeadChange(event.target.value)
            }
          >
            <option value="">
              Choose a company...
            </option>

            {leads.map((lead) => (
              <option key={lead.id} value={lead.id}>
                {lead.company_name} (#{lead.id})
              </option>
            ))}
          </select>
        </label>

        {loadingLeads && (
          <p className="mt-3 text-sm text-slate-500">
            Loading leads...
          </p>
        )}
      </section>
        
    {/* Step 2: AI Solution Matching */}
    <SolutionMatchingPanel
      key={`matching-${selectedLeadId ?? "no-lead"}`}
      leadId={selectedLeadId}
    />

    {/* Step 3: Contact Discovery */}
    <ContactDiscoveryPanel
      key={`contacts-${selectedLeadId ?? "no-lead"}`}
      leadId={selectedLeadId}
      onSelectContact={setSelectedContact}
    />


  {selectedContact && (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm">
      <p className="font-semibold text-indigo-900">
        Selected Contact: {selectedContact.name}
      </p>
      <p className="mt-1 text-indigo-700">
        {selectedContact.job_title}
      </p>
      <p className="mt-2 text-xs text-indigo-600">
        This contact has not yet been connected to
        Email Generation.
      </p>
    </div>
  )}

      {/* Step 3: Generate Outreach */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-5 text-lg font-semibold">
          Step 4 — Generate Outreach
        </h3>

        <p className="mb-5 text-sm text-slate-500">
          Run the AI research, writing, review, and improvement
          workflow for your selected lead.
        </p>

        <label className="block space-y-2 text-sm font-medium">
          Your Product / Service Offering

          <textarea
            className={inputClass}
            rows={3}
            value={offering}
            disabled={running}
            onChange={(event) =>
              setOffering(event.target.value)
            }
          />
        </label>

        <p className="mt-2 text-xs text-slate-500">
          Currently, the email workflow uses the offering
          entered above. The Solution Matching recommendation
          is a separate preview and is not automatically
          passed to the Writer Agent yet.
        </p>

        <button
          type="button"
          onClick={() => void handleRun()}
          disabled={
            !leadId ||
            offering.trim().length < 10 ||
            running ||
            loadingHistory
          }
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 md:w-auto"
        >
          {running ? (
            <LoaderCircle
              size={18}
              className="animate-spin"
            />
          ) : (
            <Play size={18} />
          )}

          {running
            ? "Running AI Agents..."
            : "Run AI Outreach"}
        </button>

        {running && (
          <p
            role="status"
            className="mt-4 text-sm text-indigo-600"
          >
            Researching, writing, and reviewing your email.
            This can take a little while.
          </p>
        )}
      </section>

      {/* Step 4: History and Results */}
      <div className="grid items-start gap-6 xl:grid-cols-[1fr_2fr]">
        {/* Run History */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Clock3
              size={19}
              className="text-indigo-600"
            />

            <h3 className="font-semibold">
              Run History
            </h3>
          </div>

          {loadingHistory ? (
            <p className="text-sm text-slate-500">
              Loading history...
            </p>
          ) : runs.length === 0 ? (
            <p className="text-sm text-slate-500">
              Select a lead to see its outreach history.
            </p>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <button
                  key={run.id}
                  type="button"
                  onClick={() => setSelectedRun(run)}
                  className={`w-full rounded-xl border p-3 text-left text-sm transition ${
                    selectedRun?.id === run.id
                      ? "border-indigo-400 bg-indigo-50"
                      : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex justify-between gap-2">
                    <span className="font-semibold">
                      Run #{run.id}
                    </span>

                    <span className="font-medium">
                      {run.review.overall_score}/10
                    </span>
                  </div>

                  <p className="mt-1 text-xs text-slate-500">
                    {new Date(
                      run.created_at,
                    ).toLocaleString()}
                  </p>

                  <div className="mt-2">
                    {run.human_approved ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                        <CheckCircle2 size={13} />
                        Human Approved
                      </span>
                    ) : (
                      <span className="text-xs text-amber-700">
                        Awaiting Human Approval
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Selected Run */}
        <div className="space-y-6">
          {!selectedRun ? (
            <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
              <Mail
                className="mx-auto mb-3"
                size={32}
              />

              Run the workflow or select a previous result.
            </section>
          ) : (
            <>
              {/* Editable Email and Human Approval */}
              <EmailEditor
                key={selectedRun.id}
                run={selectedRun}
                onUpdate={handleRunUpdate}
              />

              {/* Gmail Draft */}
              <GmailDraftPanel
                key={selectedRun.id}
                run={selectedRun}
                recipientEmail={
                  leads.find(
                    (lead) =>
                      lead.id === selectedRun.lead_id,
                  )?.recipient_email ?? ""
                }
              />

              {/* AI Review */}
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle2
                    size={20}
                    className="text-indigo-600"
                  />

                  <h3 className="text-lg font-semibold">
                    AI Review
                  </h3>
                </div>

                <p className="mt-4 text-3xl font-bold">
                  {selectedRun.review.overall_score}

                  <span className="text-lg font-normal text-slate-400">
                    /10
                  </span>
                </p>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  {[
                    [
                      "Personalization",
                      selectedRun.review.personalization,
                    ],
                    [
                      "Clarity",
                      selectedRun.review.clarity,
                    ],
                    [
                      "Relevance",
                      selectedRun.review.relevance,
                    ],
                    [
                      "CTA Quality",
                      selectedRun.review.cta_quality,
                    ],
                  ].map(([label, score]) => (
                    <div
                      key={label}
                      className="rounded-lg bg-slate-50 p-3"
                    >
                      <p className="text-slate-500">
                        {label}
                      </p>

                      <p className="mt-1 font-semibold">
                        {score}/10
                      </p>
                    </div>
                  ))}
                </div>

                <p className="mt-4 text-sm text-slate-600">
                  Improvements performed:{" "}
                  <strong>
                    {selectedRun.improvement_count}
                  </strong>
                </p>

                {selectedRun.review.unsupported_claims.length >
                  0 && (
                  <div className="mt-4 text-sm text-red-700">
                    <p className="font-semibold">
                      Unsupported Claims
                    </p>

                    <ul className="mt-2 list-disc pl-5">
                      {selectedRun.review.unsupported_claims.map(
                        (claim, index) => (
                          <li key={index}>
                            {claim}
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                )}

                {selectedRun.review.improvement_suggestions
                  .length > 0 && (
                  <div className="mt-4 text-sm">
                    <p className="font-semibold">
                      Suggestions
                    </p>

                    <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-600">
                      {selectedRun.review.improvement_suggestions.map(
                        (suggestion, index) => (
                          <li key={index}>
                            {suggestion}
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                )}

                <p className="mt-4 text-xs text-slate-500">
                  AI scores refer to the generated draft,
                  not any subsequent human edits.
                </p>
              </section>

              {/* Company Research */}
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-lg font-semibold">
                  Company Research
                </h3>

                <div className="mt-4 space-y-3">
                  {selectedRun.research.verified_findings.map(
                    (finding, index) => (
                      <div
                        key={index}
                        className="text-sm"
                      >
                        <p>
                          {finding.claim}
                        </p>

                        <a
                          href={finding.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 inline-block text-xs text-indigo-600 hover:underline"
                        >
                          View source
                        </a>
                      </div>
                    ),
                  )}
                </div>

                <p className="mt-4 text-xs text-slate-500">
                  Sources and claims are AI-generated and
                  require verification.
                </p>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
