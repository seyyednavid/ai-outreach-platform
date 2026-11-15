import type { ButtonHTMLAttributes, ReactNode } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Info,
  LoaderCircle,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

export type Tone = "neutral" | "accent" | "ok" | "warn" | "bad";

const toneText: Record<Tone, string> = {
  neutral: "bg-paper text-ink-soft border-line",
  accent: "bg-petrol-wash text-petrol-strong border-petrol/20",
  ok: "bg-ok-wash text-ok border-ok/20",
  warn: "bg-warn-wash text-warn border-warn/20",
  bad: "bg-bad-wash text-bad border-bad/20",
};

const toneIcon: Record<Tone, LucideIcon> = {
  neutral: Info,
  accent: Info,
  ok: CheckCircle2,
  warn: TriangleAlert,
  bad: AlertCircle,
};

/* ------------------------------------------------------------------ */
/* Page structure                                                      */
/* ------------------------------------------------------------------ */

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-6">
      <div className="max-w-2xl">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 text-[15px] leading-6 text-muted">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function Card({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article" | "form";
}) {
  return (
    <Tag className={`rounded-lg border border-line bg-surface ${className}`}>
      {children}
    </Tag>
  );
}

export function CardHeader({
  title,
  description,
  step,
  icon: Icon,
  tag,
  actions,
}: {
  title: string;
  description?: string;
  step?: number;
  icon?: LucideIcon;
  tag?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 items-start gap-3">
        {step !== undefined ? (
          <span
            aria-hidden
            className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-md bg-ink font-mono text-xs font-bold text-signal"
          >
            {step}
          </span>
        ) : (
          Icon && (
            <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-md bg-petrol-wash text-petrol">
              <Icon size={16} />
            </span>
          )
        )}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold text-ink">
              {step !== undefined && <span className="sr-only">Step {step}: </span>}
              {title}
            </h2>
            {tag}
          </div>
          {description && (
            <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Controls                                                            */
/* ------------------------------------------------------------------ */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "approve";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-petrol text-white hover:bg-petrol-strong",
  approve: "bg-ok text-white hover:bg-ok/90",
  secondary:
    "border border-line-strong bg-surface text-ink hover:border-ink-soft/40 hover:bg-paper",
  ghost: "text-ink-soft hover:bg-paper hover:text-ink",
  danger: "border border-bad/30 bg-surface text-bad hover:bg-bad-wash",
};

export function Button({
  variant = "primary",
  size = "md",
  icon: Icon,
  loading = false,
  children,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  icon?: LucideIcon;
  loading?: boolean;
}) {
  const sizing =
    size === "sm" ? "gap-1.5 px-3 py-1.5 text-[13px]" : "gap-2 px-4 py-2.5 text-sm";

  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center rounded-md font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${sizing} ${buttonVariants[variant]} ${className}`}
      {...props}
    >
      {loading ? (
        <LoaderCircle size={size === "sm" ? 14 : 16} className="animate-spin" />
      ) : (
        Icon && <Icon size={size === "sm" ? 14 : 16} />
      )}
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  children,
  className = "",
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block text-sm ${className}`}>
      <span className="font-medium text-ink">{label}</span>
      {hint && <span className="ml-2 text-xs text-muted">{hint}</span>}
      <span className="mt-1.5 block">{children}</span>
    </label>
  );
}

/* ------------------------------------------------------------------ */
/* Status                                                              */
/* ------------------------------------------------------------------ */

export function Badge({
  tone = "neutral",
  icon: Icon,
  children,
}: {
  tone?: Tone;
  icon?: LucideIcon;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded border px-2 py-0.5 text-xs font-semibold ${toneText[tone]}`}
    >
      {Icon && <Icon size={12} />}
      {children}
    </span>
  );
}

export function Notice({
  tone = "neutral",
  title,
  children,
  role,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
  role?: "alert" | "status";
}) {
  const Icon = toneIcon[tone];

  return (
    <div
      role={role ?? (tone === "bad" ? "alert" : undefined)}
      className={`flex gap-2.5 rounded-md border px-3.5 py-3 text-sm leading-6 ${toneText[tone]}`}
    >
      <Icon size={16} className="mt-1 shrink-0" />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? "mt-0.5" : ""}>{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-line-strong px-6 py-12 text-center">
      <Icon size={26} className="text-muted" />
      <p className="mt-3 font-semibold text-ink">{title}</p>
      {children && (
        <p className="mt-1 max-w-sm text-sm leading-6 text-muted">{children}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-muted">
      {children}
    </p>
  );
}
