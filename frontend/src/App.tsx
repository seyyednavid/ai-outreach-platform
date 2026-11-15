
import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Drafts from "./pages/Drafts";
import Leads from "./pages/Leads";
import MyCompany from "./pages/MyCompany";
import Outreach from "./pages/Outreach";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="company" element={<MyCompany />} />
          <Route path="/leads" element={<Leads />} />
          {/* Outreach is two pages: write a new draft, then review drafts. */}
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/drafts" element={<Drafts />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
