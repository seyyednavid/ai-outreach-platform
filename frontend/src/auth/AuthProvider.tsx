import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";

import { getMe } from "../api/admin";
import { authConfigured, supabase } from "../lib/supabase";
import { AuthContext, type AuthState } from "./auth-context";

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(authConfigured);
  // Owner status, per signed-in user id.
  const [owner, setOwner] = useState<{ userId: string; isOwner: boolean } | null>(null);
  const userId = session?.user.id ?? null;

  useEffect(() => {
    if (!authConfigured) return;

    // Also picks up the session from an email confirmation link.
    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setLoading(false);
    });

    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    getMe()
      .then((me) => {
        if (!cancelled) setOwner({ userId, isOwner: me.is_admin });
      })
      .catch(() => {
        // Treat as a customer; the owner pages also check on the server.
        if (!cancelled) setOwner({ userId, isOwner: false });
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const isOwner = userId && owner?.userId === userId ? owner.isOwner : null;

  const value = useMemo<AuthState>(
    () => ({
      session,
      loading,
      isOwner,
      signOut: async () => {
        await supabase.auth.signOut();
      },
    }),
    [session, loading, isOwner],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
