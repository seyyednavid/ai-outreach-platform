import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoaderCircle } from "lucide-react";

import AuthProvider from "./auth/AuthProvider";
import { useAuth } from "./auth/auth-context";
import AppLayout from "./components/AppLayout";
import { Notice } from "./components/ui";
import { authConfigured } from "./lib/supabase";
import Dashboard from "./pages/Dashboard";
import Drafts from "./pages/Drafts";
import Leads from "./pages/Leads";
import Login from "./pages/Login";
import MyCompany from "./pages/MyCompany";
import Outreach from "./pages/Outreach";
import OwnerCustomers from "./pages/OwnerCustomers";
import OwnerOverview from "./pages/OwnerOverview";
import OwnerRuns from "./pages/OwnerRuns";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <SignedInApp />
      </BrowserRouter>
    </AuthProvider>
  );
}

/** Every page needs a signed-in user; otherwise the login page is shown. */
function SignedInApp() {
  const { session, loading, isOwner } = useAuth();

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <Notice tone="warn" title="Login is not set up">
          Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to frontend/.env, then restart
          the frontend.
        </Notice>
      </div>
    );
  }

  if (loading || (session && isOwner === null)) {
    return (
      <div className="grid min-h-screen place-items-center bg-paper text-muted" role="status">
        <LoaderCircle className="animate-spin" aria-label="Loading" />
      </div>
    );
  }

  if (!session) return <Login />;

  // Keyed by user, so nothing from a previous account stays on screen.
  return (
    <Routes key={session.user.id}>
      <Route element={<AppLayout />}>
        {/* Owners start in their console, customers in their workspace. */}
        <Route path="/" element={<Navigate to={isOwner ? "/owner" : "/dashboard"} replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="company" element={<MyCompany />} />
        <Route path="/leads" element={<Leads />} />
        {/* Outreach is two pages: write a new draft, then review drafts. */}
        <Route path="/outreach" element={<Outreach />} />
        <Route path="/drafts" element={<Drafts />} />
        {/* Owner Console. The API also refuses everyone else (404). */}
        {isOwner && (
          <>
            <Route path="/owner" element={<OwnerOverview />} />
            <Route path="/owner/customers" element={<OwnerCustomers />} />
            <Route path="/owner/runs" element={<OwnerRuns />} />
          </>
        )}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
