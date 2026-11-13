
import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Leads from "./pages/Leads";
import Outreach from "./pages/Outreach";
import MyCompany from "./pages/MyCompany";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="company" element={<MyCompany />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/outreach" element={<Outreach />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
