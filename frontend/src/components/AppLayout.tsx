import { NavLink, Outlet } from "react-router-dom";
import {
  Building2,
  FilePlus,
  Inbox,
  LayoutDashboard,
  Users,
} from "lucide-react";

// In the order you use them: set up, then write, then review.
const navigation = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/company", label: "My Company", icon: Building2 },
  { to: "/leads", label: "Leads", icon: Users },
  { to: "/outreach", label: "New draft", icon: FilePlus },
  { to: "/drafts", label: "Drafts", icon: Inbox },
];

const pipeline = ["Research", "Write", "Review", "Improve ×2", "You approve", "Gmail draft"];

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-paper text-ink md:flex">
      <aside className="bg-ink text-white md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0">
        <div className="flex h-full flex-col px-4 py-4 md:px-5 md:py-7">
          {/* Brand */}
          <div className="flex items-center gap-3 px-1">
            <span
              aria-hidden
              className="grid size-9 place-items-center rounded-md bg-display font-mono text-sm font-bold text-signal ring-1 ring-white/10"
            >
              AO
            </span>
            <div>
              <p className="font-display text-lg font-bold leading-none tracking-tight">
                AI Outreach
              </p>
              <p className="mt-1 text-xs text-white/55">Human-approved drafts</p>
            </div>
          </div>

          {/* Navigation */}
          <nav
            aria-label="Main"
            className="-mx-1 mt-4 flex gap-1 overflow-x-auto px-1 md:mt-9 md:flex-col md:overflow-visible"
          >
            {navigation.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-2 rounded-md px-2.5 py-2 text-sm font-medium transition-colors md:gap-3 md:px-3 md:py-2.5 ${
                    isActive
                      ? "bg-white/10 text-white shadow-[inset_2px_0_0_var(--color-signal)]"
                      : "text-white/65 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <Icon size={17} className="hidden sm:block" />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* The real sequence every draft goes through */}
          <div className="mt-auto hidden pt-8 md:block">
            <p className="font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-white/45">
              Every draft
            </p>
            <ol className="ml-1 mt-3 space-y-2 border-l border-white/15 pl-4">
              {pipeline.map((stage, index) => (
                <li key={stage} className="relative text-[13px] leading-4 text-white/70">
                  <span
                    aria-hidden
                    className={`absolute -left-[19.5px] top-[5px] size-1.5 rounded-full ${
                      index >= 4 ? "bg-signal" : "bg-white/45"
                    }`}
                  />
                  {stage}
                </li>
              ))}
            </ol>
            <p className="mt-4 text-xs leading-5 text-white/45">
              Nothing is ever sent automatically.
            </p>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 md:px-10 md:py-9">
        <div className="mx-auto max-w-[1280px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
