import { apiFetch } from "./http";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";

export interface Me {
  email: string | null;
  /** A product owner (ADMIN_EMAILS), not a customer role. */
  is_admin: boolean;
}

export interface OrganizationUsage {
  organization_id: number;
  name: string;
  user_emails: string[];
  drafts: number;
  approved_drafts: number;
  llm_requests: number;
  input_tokens: number;
  output_tokens: number;
  /** Model tokens only; web search calls are billed separately. */
  estimated_cost_usd: number;
  last_draft_at: string | null;
}

export interface UsageOverview {
  organizations: OrganizationUsage[];
  total_drafts: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
}

export interface QualityStats {
  drafts: number;
  /** The AI's own draft passed review (score 8+, no flags left). */
  ai_passed: number;
  first_try_passed: number;
  average_score: number | null;
  average_rewrites: number | null;
  edited_by_human: number;
  edits_checked_by_ai: number;
  edits_failed_check: number;
  human_approved: number;
  /** Approved although the latest AI review failed. */
  overrides: number;
  flags_kept: number;
  /** Reviewer flags dropped by code (quote not in the email, or supported). */
  flags_ignored_by_code: number;
  placeholder_flags: number;
  missing_signature_flags: number;
}

export interface OwnerOverview {
  customers: number;
  users: number;
  drafts: number;
  drafts_last_7_days: number;
  total_tokens: number;
  estimated_cost_usd: number;
  average_cost_per_draft_usd: number | null;
  quality: QualityStats;
}

export interface RunUsage {
  id: number;
  organization_id: number;
  organization_name: string | null;
  lead_id: number;
  lead_run_number: number;
  created_at: string;
  overall_score: number | null;
  approved: boolean;
  improvement_count: number;
  human_approved: boolean;
  review_override: boolean;
  llm_requests: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  trace_url: string | null;
  recheck_trace_url: string | null;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await apiFetch(`${API_BASE_URL}${path}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(
      response.status === 404 ? "This page is only for the product owner." : `Request failed (${response.status})`,
    );
  }

  return response.json() as Promise<T>;
}

export function getMe(): Promise<Me> {
  return getJson<Me>("/me");
}

export function getUsage(): Promise<UsageOverview> {
  return getJson<UsageOverview>("/admin/usage");
}

export function getOwnerOverview(): Promise<OwnerOverview> {
  return getJson<OwnerOverview>("/admin/overview");
}

/** Latest runs across all customers, or for one customer. */
export function getRecentRuns(organizationId?: number): Promise<RunUsage[]> {
  const query = organizationId === undefined ? "" : `?organization_id=${organizationId}`;
  return getJson<RunUsage[]>(`/admin/runs${query}`);
}
