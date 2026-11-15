import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const key = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ??
  import.meta.env.VITE_SUPABASE_ANON_KEY) as string | undefined;

/** False when frontend/.env is missing the Supabase settings. */
export const authConfigured = Boolean(url && key);

// Placeholders keep the app loadable; App shows a setup message instead.
export const supabase = createClient(url ?? "http://localhost", key ?? "not-configured");
