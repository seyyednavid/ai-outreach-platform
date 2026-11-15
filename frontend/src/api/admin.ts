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

export interface RunUsage {
  id: number;
  lead_id: number;
  lead_run_number: number;
  created_at: string;
  approved: boolean;
  human_approved: boolean;
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

export function getOrganizationRuns(organizationId: number): Promise<RunUsage[]> {
  return getJson<RunUsage[]>(`/admin/organizations/${organizationId}/runs`);
}
