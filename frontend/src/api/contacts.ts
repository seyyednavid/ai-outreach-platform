
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";

export interface ReviewedContact {
  name: string;
  job_title: string;
  company_name: string;
  relevance_reason: string;

  source_url: string;
  source_excerpt: string;

  public_work_email: string | null;
  email_source_url: string | null;

  relevance_score: number;
  evidence_status: string;
  evidence_warnings: string[];
}

export interface ContactDiscoveryResponse {
  lead_id: number;
  target_company: string;
  contacts: ReviewedContact[];
  search_summary: string;
  limitations: string[];
}

export async function discoverContacts(
  leadId: number,
): Promise<ContactDiscoveryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/contacts/discover`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        lead_id: leadId,
      }),
    },
  );

  if (!response.ok) {
    let message = `Contact discovery failed (${response.status})`;

    try {
      const error = await response.json();

      if (typeof error.detail === "string") {
        message = error.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<ContactDiscoveryResponse>;
}
