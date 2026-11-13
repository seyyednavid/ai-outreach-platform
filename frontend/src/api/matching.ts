
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";

export interface SolutionMatchResponse {
  company_id: number;
  lead_id: number;
  recommended_product_id: number | null;
  recommended_product_name: string | null;
  potential_use_case: string;
  reasoning: string;
  confidence: "low" | "medium" | "high";
  customer_need_verified: boolean;
  missing_information: string[];
}

export async function previewSolutionMatch(
  companyId: number,
  leadId: number,
): Promise<SolutionMatchResponse> {
  const response = await fetch(`${API_BASE_URL}/matching/preview`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      company_id: companyId,
      lead_id: leadId,
    }),
  });

  if (!response.ok) {
    let message = `Matching failed (${response.status})`;

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      // Keep default error message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<SolutionMatchResponse>;
}
