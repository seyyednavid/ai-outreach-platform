const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";

export interface ResearchFinding {
  claim: string;
  source_url: string;
}

export interface ResearchReport {
  company_name: string;
  industry: string;
  verified_findings: ResearchFinding[];
  potential_pain_points: string[];
  suggested_solution: string;
  personalization_angle: string;
}

export interface EmailDraft {
  subject: string;
  body: string;
  call_to_action: string;
}

export interface EmailReview {
  personalization: number;
  clarity: number;
  relevance: number;
  cta_quality: number;
  /** Flags whose quoted text was found in the email. */
  unsupported_claims: string[];
  improvement_suggestions: string[];
  /** Flags dropped because their quote is not in the email. Missing on older reviews. */
  ignored_claims?: string[];
  overall_score: number;
  approved: boolean;
}

/** Audit snapshot of what the AI workflow was given for a run. */
export interface OutreachRunContext {
  sender_offering: string;
  /** Detail fields are missing on runs created before 15 Nov 2026. */
  seller_company: {
    id: number;
    name: string;
    industry?: string | null;
    description?: string | null;
    target_customers?: string | null;
    differentiators?: string | null;
    sender_name?: string | null;
    cta_type?: string | null;
  } | null;
  selected_product: {
    id: number;
    name: string;
    description?: string | null;
    features?: string[] | null;
    use_cases?: string[] | null;
  } | null;
  selected_contact: {
    name: string;
    reported_job_title: string;
    source_url: string;
    client_evidence_status: string;
    backend_verification_status: "NOT_VERIFIED";
  } | null;
}

export interface OutreachRun {
  /** Global number across all leads. */
  id: number;
  lead_id: number;
  /** Run 1, 2, 3 ... within this lead. */
  lead_run_number: number;
  research: ResearchReport;
  email: EmailDraft;
  /** The AI's review of its own final draft. */
  review: EmailReview;
  /** The AI's review of your edited version, if you asked for one. */
  final_review: EmailReview | null;
  /** Null for runs created before context snapshots existed. */
  context: OutreachRunContext | null;
  /** True when the AI's own draft passed review. */
  approved: boolean;
  /** The review that decides approval: of your edits when checked. */
  review_passed: boolean;
  improved: boolean;
  improvement_count: number;
  requires_human_review: boolean;
  created_at: string;
  final_email: EmailDraft | null;
  human_approved: boolean;
  /** True when a human approved despite a failed AI review. */
  review_override: boolean;
  approved_at: string | null;
}

export interface SelectedOutreachContact {
  name: string;
  job_title: string;
  source_url: string;
  evidence_status: "VERIFIED" | "NEEDS_REVIEW" | "EXCERPT_CONSISTENT";
}

export interface OutreachRunPayload {
  lead_id: number;
  sender_offering: string;
  seller_company_id?: number;
  selected_product_id?: number;
  selected_contact?: SelectedOutreachContact;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: unknown = await response.json().catch(() => null);
    const detail =
      typeof error === "object" && error !== null && "detail" in error
        ? error.detail
        : null;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status})`,
    );
  }
  return (await response.json()) as T;
}

export async function runOutreach(
  payload: OutreachRunPayload,
): Promise<OutreachRun> {
  const response = await fetch(`${API_BASE_URL}/outreach/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<OutreachRun>(response);
}

/** The newest drafts across all leads. */
export async function getRecentRuns(): Promise<OutreachRun[]> {
  const response = await fetch(`${API_BASE_URL}/outreach/runs`);
  return parseResponse<OutreachRun[]>(response);
}

export async function getLeadRuns(leadId: number): Promise<OutreachRun[]> {
  const response = await fetch(
    `${API_BASE_URL}/outreach/leads/${leadId}/runs`,
  );
  return parseResponse<OutreachRun[]>(response);
}

export async function saveEmailDraft(
  runId: number,
  email: EmailDraft,
): Promise<OutreachRun> {
  const response = await fetch(
    `${API_BASE_URL}/outreach/runs/${runId}/draft`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    },
  );
  return parseResponse<OutreachRun>(response);
}

/** Ask the AI reviewer to check your edited version. Never changes the text. */
export async function recheckEmailDraft(runId: number): Promise<OutreachRun> {
  const response = await fetch(
    `${API_BASE_URL}/outreach/runs/${runId}/review`,
    { method: "POST" },
  );
  return parseResponse<OutreachRun>(response);
}

export async function approveEmailDraft(
  runId: number,
  acknowledgeFailedReview = false,
): Promise<OutreachRun> {
  const response = await fetch(
    `${API_BASE_URL}/outreach/runs/${runId}/approve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        acknowledge_failed_review: acknowledgeFailedReview,
      }),
    },
  );
  return parseResponse<OutreachRun>(response);
}
