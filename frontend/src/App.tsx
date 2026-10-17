import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DatasetProvider } from "./context/DatasetContext";
import Layout from "./components/Layout";

import UploadExplore from "./pages/UploadExplore";
import ChatAnalytics from "./pages/ChatAnalytics";
import Dashboard from "./pages/Dashboard";
import Insights from "./pages/Insights";
import AdvancedAnalytics from "./pages/AdvancedAnalytics";
import CPIForecasting from "./pages/CPIForecasting";
import ExecutiveReport from "./pages/ExecutiveReport";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <DatasetProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<UploadExplore />} />
            <Route path="chat" element={<ChatAnalytics />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="insights" element={<Insights />} />
            <Route path="advanced" element={<AdvancedAnalytics />} />
            <Route path="cpi" element={<CPIForecasting />} />
            <Route path="report" element={<ExecutiveReport />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </DatasetProvider>
    </BrowserRouter>
  );
}