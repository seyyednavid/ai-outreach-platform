
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
  unsupported_claims: string[];
  improvement_suggestions: string[];
  overall_score: number;
  approved: boolean;
}

export interface OutreachRun {
  id: number;
  lead_id: number;
  research: ResearchReport;
  email: EmailDraft;
  review: EmailReview;
  approved: boolean;
  improved: boolean;
  improvement_count: number;
  requires_human_review: boolean;
  created_at: string;
  final_email: EmailDraft | null;
  human_approved: boolean;
  approved_at: string | null;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : `Request failed (${response.status})`,
    );
  }
  return response.json() as Promise<T>;
}

export async function runOutreach(
  leadId: number,
  senderOffering: string,
): Promise<OutreachRun> {
  const response = await fetch(`${API_BASE_URL}/outreach/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lead_id: leadId,
      sender_offering: senderOffering,
    }),
  });

  return parseResponse<OutreachRun>(response);
}

export async function getLeadRuns(
  leadId: number,
): Promise<OutreachRun[]> {
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

export async function approveEmailDraft(
  runId: number,
): Promise<OutreachRun> {
  const response = await fetch(
    `${API_BASE_URL}/outreach/runs/${runId}/approve`,
    { method: "POST" },
  );

  return parseResponse<OutreachRun>(response);
}

