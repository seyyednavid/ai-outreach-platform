
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";

export interface Lead {
  id: number;
  company_name: string;
  website: string | null;
  industry: string;
  target_role: string;
  pain_point: string;
  recipient_name: string | null;
  recipient_email: string | null;
}

export type LeadCreate = Omit<Lead, "id">;

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const error = await response.json();
      if (typeof error.detail === "string") {
        message = error.detail;
      } else if (response.status === 422) {
        message = "Please check the form fields.";
      }
    } catch {
      // Use the HTTP status message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getLeads(): Promise<Lead[]> {
  const response = await fetch(`${API_BASE_URL}/leads`);
  return parseResponse<Lead[]>(response);
}

export async function createLead(
  data: LeadCreate,
): Promise<Lead> {
  const response = await fetch(`${API_BASE_URL}/leads`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return parseResponse<Lead>(response);
}
