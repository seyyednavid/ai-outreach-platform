import { apiFetch } from "./http";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";


export interface GmailStatus {
  connected: boolean;
}

export interface GmailDraftResponse {
  run_id: number;
  draft_id: string;
  status: string;
}

async function parseResponse<T>(
  response: Response,
): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    try {
      const error = await response.json();

      if (typeof error.detail === "string") {
        message = error.detail;
      }
    } catch {
      // Use the HTTP error message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

/** Google's consent page for the signed-in user. */
export async function getGmailConnectUrl(): Promise<string> {
  const response = await apiFetch(`${API_BASE_URL}/gmail/connect`);
  const data = await parseResponse<{ authorization_url: string }>(response);
  return data.authorization_url;
}

export async function getGmailStatus(): Promise<GmailStatus> {
  const response = await apiFetch(
    `${API_BASE_URL}/gmail/status`,
  );

  return parseResponse<GmailStatus>(response);
}

export async function createGmailDraft(
  runId: number,
  recipientEmail: string,
): Promise<GmailDraftResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/gmail/drafts`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        run_id: runId,
        recipient_email: recipientEmail,
      }),
    },
  );

  return parseResponse<GmailDraftResponse>(response);
}
