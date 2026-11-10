
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Mail,
  Sparkles,
} from "lucide-react";

const navigation = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/leads", label: "Leads", icon: Users },
  { to: "/outreach", label: "Outreach", icon: Mail },
];

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 md:flex">
      <aside className="w-full bg-slate-950 p-6 text-white md:min-h-screen md:w-64">
        <div className="mb-10 flex items-center gap-3">
          <div className="rounded-xl bg-indigo-500 p-2">
            <Sparkles size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold">AI Outreach</h1>
            <p className="text-xs text-slate-400">
              Intelligent Sales Platform
            </p>
          </div>
        </div>

        <nav className="flex gap-2 md:flex-col">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-4 py-3 text-sm transition ${
                  isActive
                    ? "bg-indigo-600 text-white"
                    : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-12 hidden rounded-xl bg-slate-900 p-4 md:block">
          <p className="text-sm font-medium">Agent Workflow</p>
          <p className="mt-2 text-xs text-slate-400">
            Research → Write → Review → Improve
          </p>
        </div>
      </aside>

      <main className="min-w-0 flex-1 p-5 md:p-10">
        <Outlet />
      </main>
    </div>
  );
}
