import { supabase } from "../lib/supabase";

/**
 * fetch() with the signed-in user's access token. Supabase refreshes
 * the token automatically before it expires.
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(input, { ...init, headers });

  // The backend no longer accepts this session: show the login page.
  if (response.status === 401 && token) {
    await supabase.auth.signOut({ scope: "local" });
  }

  return response;
}
