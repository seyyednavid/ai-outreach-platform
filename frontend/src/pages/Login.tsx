import { useState, type FormEvent } from "react";
import { LogIn, UserPlus } from "lucide-react";

import { Button, Field, Notice } from "../components/ui";
import { inputClass } from "../components/ui-classes";
import { supabase } from "../lib/supabase";

type Mode = "sign-in" | "sign-up";

const MIN_PASSWORD = 8;

const pipeline = ["Research", "Write", "Review", "Improve ×2", "You approve", "Gmail draft"];

/** Supabase messages, in the app's words. */
function friendlyError(message: string): string {
  if (/invalid login credentials/i.test(message)) return "Email or password is incorrect.";
  if (/email not confirmed/i.test(message)) {
    return "Confirm your email first. Open the link Supabase sent to your inbox.";
  }
  if (/rate limit/i.test(message)) return "Too many attempts. Wait a minute and try again.";
  return message;
}

export default function Login() {
  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  const signingUp = mode === "sign-up";

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setSentTo(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError(null);
    try {
      if (signingUp) {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: { emailRedirectTo: window.location.origin },
        });
        if (signUpError) throw signUpError;
        // With email confirmation on, there is no session until the link is opened.
        if (!data.session) {
          setSentTo(email.trim());
          setPassword("");
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (signInError) throw signInError;
      }
    } catch (err) {
      setError(friendlyError(err instanceof Error ? err.message : "Something went wrong."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-paper text-ink lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      {/* What the product does */}
      <aside className="bg-ink px-6 py-8 text-white md:px-12 lg:flex lg:flex-col lg:py-14">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="grid size-9 place-items-center rounded-md bg-display font-mono text-sm font-bold text-signal ring-1 ring-white/10"
          >
            AO
          </span>
          <p className="font-display text-lg font-bold leading-none tracking-tight">AI Outreach</p>
        </div>

        <h1 className="mt-10 max-w-md font-display text-3xl font-bold leading-tight tracking-tight md:text-4xl lg:mt-auto">
          B2B emails researched and checked by AI, approved by you.
        </h1>
        <p className="mt-4 max-w-md text-[15px] leading-6 text-white/65">
          Every draft follows the same path, and nothing is ever sent automatically.
        </p>

        <ol className="mt-8 hidden flex-wrap gap-2 sm:flex lg:mb-auto">
          {pipeline.map((stage, index) => (
            <li
              key={stage}
              className={`rounded border px-2.5 py-1 font-mono text-xs ${
                index >= 4 ? "border-signal/40 text-signal" : "border-white/15 text-white/70"
              }`}
            >
              {stage}
            </li>
          ))}
        </ol>
      </aside>

      {/* Form */}
      <main className="flex items-center justify-center px-4 py-10 md:px-10">
        <div className="w-full max-w-sm">
          <h2 className="font-display text-2xl font-bold tracking-tight">
            {signingUp ? "Create your account" : "Sign in"}
          </h2>
          <p className="mt-1.5 text-sm text-muted">
            {signingUp
              ? "Your companies, leads and drafts are private to your account."
              : "Welcome back. Sign in to see your drafts."}
          </p>

          {sentTo ? (
            <div className="mt-6 space-y-4">
              <Notice tone="ok" title="Check your inbox" role="status">
                We sent a confirmation link to <strong>{sentTo}</strong>. Open it, and you are
                signed in.
              </Notice>
              <Button variant="secondary" className="w-full" onClick={() => switchMode("sign-in")}>
                Back to sign in
              </Button>
            </div>
          ) : (
            <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
              {error && <Notice tone="bad">{error}</Notice>}

              <Field label="Email">
                <input
                  type="email"
                  className={inputClass}
                  value={email}
                  required
                  autoComplete="email"
                  disabled={busy}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>

              <Field
                label="Password"
                hint={signingUp ? `At least ${MIN_PASSWORD} characters` : undefined}
              >
                <input
                  type="password"
                  className={inputClass}
                  value={password}
                  required
                  minLength={signingUp ? MIN_PASSWORD : undefined}
                  autoComplete={signingUp ? "new-password" : "current-password"}
                  disabled={busy}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>

              <Button
                type="submit"
                icon={signingUp ? UserPlus : LogIn}
                loading={busy}
                disabled={busy}
                className="w-full"
              >
                {signingUp ? "Create account" : "Sign in"}
              </Button>
            </form>
          )}

          {!sentTo && (
            <p className="mt-6 text-center text-sm text-muted">
              {signingUp ? "Already have an account?" : "New here?"}{" "}
              <button
                type="button"
                className="font-semibold text-petrol hover:underline"
                onClick={() => switchMode(signingUp ? "sign-in" : "sign-up")}
              >
                {signingUp ? "Sign in" : "Create an account"}
              </button>
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
