/** Shared form control styling, kept separate so ui.tsx only exports components. */
export const inputClass =
  "w-full rounded-md border border-line-strong bg-surface px-3 py-2.5 " +
  "text-sm text-ink placeholder:text-muted/70 outline-none transition " +
  "focus:border-petrol focus:ring-2 focus:ring-petrol/15 " +
  "disabled:cursor-not-allowed disabled:bg-paper disabled:text-muted";

/** A link that looks like the primary Button. */
export const linkButtonClass =
  "inline-flex items-center justify-center gap-2 rounded-md bg-petrol px-4 py-2.5 " +
  "text-sm font-semibold text-white transition-colors hover:bg-petrol-strong";

export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
