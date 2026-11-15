import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Play } from "lucide-react";

import { getCompanies, type Company } from "../api/companies";
import { type ReviewedContact } from "../api/contacts";
import { getLeads, type Lead } from "../api/leads";
import { type SolutionMatchResponse } from "../api/matching";
import { runOutreach, type SelectedOutreachContact } from "../api/outreach";

import ContactDiscoveryPanel from "../components/ContactDiscoveryPanel";
import SolutionMatchingPanel from "../components/SolutionMatchingPanel";
import { Badge, Button, Card, CardHeader, Field, Label, Notice, PageHeader } from "../components/ui";
import { getErrorMessage, inputClass } from "../components/ui-classes";

const defaultOffering =
  "We provide queue management and customer flow solutions for retail environments.";

function toSelectedContact(contact: ReviewedContact | null): SelectedOutreachContact | undefined {
  if (!contact) return undefined;
  switch (contact.evidence_status) {
    case "VERIFIED":
    case "NEEDS_REVIEW":
    case "EXCERPT_CONSISTENT":
      return {
        name: contact.name,
        job_title: contact.job_title,
        source_url: contact.source_url,
        evidence_status: contact.evidence_status,
      };
    default:
      return undefined;
  }
}

/** Page 1 of 2: choose what the AI should write, then generate. */
export default function Outreach() {
  const navigate = useNavigate();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [leadId, setLeadId] = useState<number | null>(null);
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [offering, setOffering] = useState(defaultOffering);
  const [selectedMatch, setSelectedMatch] = useState<SolutionMatchResponse | null>(null);
  const [selectedContact, setSelectedContact] = useState<ReviewedContact | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getLeads(), getCompanies()])
      .then(([leadData, companyData]) => {
        if (cancelled) return;
        setLeads(leadData);
        setCompanies(companyData);
        if (companyData.length === 1) setCompanyId(companyData[0].id);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, "Could not load your leads and companies."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const lead = leads.find((item) => item.id === leadId) ?? null;
  const company = companies.find((item) => item.id === companyId) ?? null;
  const match =
    selectedMatch?.lead_id === leadId &&
    selectedMatch.company_id === companyId &&
    selectedMatch.recommended_product_id !== null
      ? selectedMatch
      : null;
  const offeringValid = offering.trim().length >= 10;
  const hasSignature = Boolean(company?.sender_name);
  const canRun = leadId !== null && companyId !== null && offeringValid && !running;

  function chooseLead(value: string) {
    setLeadId(value ? Number(value) : null);
    setSelectedMatch(null);
    setSelectedContact(null);
    setError(null);
  }

  function chooseCompany(value: string) {
    setCompanyId(value ? Number(value) : null);
    setSelectedMatch(null);
    setError(null);
  }

  async function handleRun() {
    if (!canRun || leadId === null || companyId === null) return;
    const contact = toSelectedContact(selectedContact);

    setRunning(true);
    setError(null);
    try {
      const result = await runOutreach({
        lead_id: leadId,
        sender_offering: offering.trim(),
        seller_company_id: companyId,
        ...(match ? { selected_product_id: match.recommended_product_id! } : {}),
        ...(contact ? { selected_contact: contact } : {}),
      });
      navigate(`/drafts?lead=${leadId}&run=${result.id}`);
    } catch (err) {
      setError(
        getErrorMessage(err, "The AI workflow failed. Your choices are kept, so you can try again."),
      );
      setRunning(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="New draft"
        description="Step 1 of 2. Tell the AI who to write to and what to offer. Next, you review and approve the draft on the Drafts page."
      />

      {error && <Notice tone="bad">{error}</Notice>}

      <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          {/* 1. Lead */}
          <Card className="p-5 md:p-6">
            <CardHeader step={1} title="Choose a lead" description="The company you want to reach." />
            <div className="mt-5">
              <Field label="Lead">
                <select
                  className={inputClass}
                  value={leadId ?? ""}
                  disabled={loading || running}
                  onChange={(event) => chooseLead(event.target.value)}
                >
                  <option value="">{loading ? "Loading leads…" : "Choose a company…"}</option>
                  {leads.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.company_name} — {item.industry}
                    </option>
                  ))}
                </select>
              </Field>
              {!loading && leads.length === 0 && (
                <p className="mt-3 text-sm text-muted">
                  No leads yet. <Link to="/leads" className="font-medium text-petrol hover:underline">Add one on the Leads page</Link>.
                </p>
              )}
              {lead && (
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
                  <p className="leading-6 text-muted">
                    Role to reach: <span className="text-ink-soft">{lead.target_role}</span>
                  </p>
                  {lead.run_count > 0 && (
                    <Link
                      to={`/drafts?lead=${lead.id}`}
                      className="inline-flex items-center gap-1 font-medium text-petrol hover:underline"
                    >
                      {lead.run_count} earlier draft{lead.run_count === 1 ? "" : "s"} <ArrowRight size={14} />
                    </Link>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* 2. Company and signature */}
          <Card className="p-5 md:p-6">
            <CardHeader
              step={2}
              title="Choose your company"
              description="Your company signs the email and decides how it ends: a phone call or an email reply."
            />
            <div className="mt-5 space-y-3">
              <Field label="Your company">
                <select
                  className={inputClass}
                  value={companyId ?? ""}
                  disabled={loading || running}
                  onChange={(event) => chooseCompany(event.target.value)}
                >
                  <option value="">{loading ? "Loading…" : "Choose your company…"}</option>
                  {companies.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </Field>
              {company &&
                (hasSignature ? (
                  <div className="rounded-md border border-line bg-paper/60 px-4 py-3 text-sm">
                    <Label>Signature and ending</Label>
                    <p className="mt-1 text-ink">
                      {company.sender_name}
                      {company.sender_job_title && `, ${company.sender_job_title}`}
                    </p>
                    <p className="text-muted">
                      Asks for {company.cta_type === "email" ? "a reply by email" : "a short phone call"}
                    </p>
                  </div>
                ) : (
                  <Notice tone="warn" title="No sender details yet">
                    Without your name the draft cannot pass review.{" "}
                    <Link to="/company" className="font-semibold underline underline-offset-2">
                      Add them in My Company
                    </Link>
                    .
                  </Notice>
                ))}
            </div>
          </Card>

          {/* 3. Product (optional) */}
          <SolutionMatchingPanel
            key={`match-${leadId ?? "none"}-${companyId ?? "none"}`}
            step={3}
            leadId={leadId}
            companyId={companyId}
            onMatchChange={setSelectedMatch}
          />

          {/* 4. Contact (optional) */}
          <ContactDiscoveryPanel
            key={`contacts-${leadId ?? "none"}`}
            step={4}
            leadId={leadId}
            onSelectContact={setSelectedContact}
          />

          {/* 5. Offering */}
          <Card className="p-5 md:p-6">
            <CardHeader
              step={5}
              title="Describe your offering"
              description="One or two sentences. The AI may only claim what is written here or in your product catalogue."
            />
            <div className="mt-5">
              <Field label="Offering" hint={offeringValid ? undefined : "At least 10 characters"}>
                <textarea
                  className={`${inputClass} leading-6`}
                  rows={3}
                  value={offering}
                  disabled={running}
                  onChange={(event) => setOffering(event.target.value)}
                />
              </Field>
            </div>
          </Card>
        </div>

        {/* Run brief */}
        <aside className="lg:sticky lg:top-6">
          <Card className="overflow-hidden">
            <div className="border-b border-line bg-ink px-5 py-3">
              <p className="font-mono text-[11px] font-bold uppercase tracking-[0.12em] text-signal">
                Run brief
              </p>
            </div>
            <dl className="divide-y divide-line text-sm">
              <BriefRow label="Lead" value={lead?.company_name} empty="Not chosen" />
              <BriefRow
                label="Signed by"
                value={company ? company.sender_name ?? undefined : undefined}
                empty={company ? "No sender name" : "Choose your company"}
                warn={company !== null && !hasSignature}
              />
              <div className="px-5 py-3.5">
                <dt><Label>Product</Label></dt>
                <dd className="mt-1">
                  {match ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-ink">{match.recommended_product_name}</span>
                      <Badge tone="warn">Fit unconfirmed</Badge>
                    </span>
                  ) : (
                    <span className="text-muted">Offering text only</span>
                  )}
                </dd>
              </div>
              <div className="px-5 py-3.5">
                <dt><Label>Contact</Label></dt>
                <dd className="mt-1">
                  {selectedContact ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-ink">{selectedContact.name}</span>
                      <Badge tone="warn">Not verified</Badge>
                    </span>
                  ) : (
                    <span className="text-muted">Neutral greeting</span>
                  )}
                </dd>
              </div>
            </dl>
            <div className="border-t border-line px-5 py-4">
              <Button
                icon={Play}
                loading={running}
                disabled={!canRun}
                onClick={() => void handleRun()}
                className="w-full"
              >
                {running ? "Writing your draft…" : "Generate draft"}
              </Button>
              <p className="mt-3 text-xs leading-5 text-muted" role={running ? "status" : undefined}>
                {running
                  ? "Researching, writing and checking. Usually 15–30 seconds."
                  : leadId === null || companyId === null
                    ? "Choose a lead and your company to start."
                    : "Nothing is sent. You review and approve the draft next."}
              </p>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function BriefRow({
  label,
  value,
  empty,
  warn = false,
}: {
  label: string;
  value: string | undefined;
  empty: string;
  warn?: boolean;
}) {
  return (
    <div className="px-5 py-3.5">
      <dt><Label>{label}</Label></dt>
      <dd className={`mt-1 ${value ? "font-medium text-ink" : warn ? "font-medium text-warn" : "text-muted"}`}>
        {value ?? empty}
      </dd>
    </div>
  );
}
