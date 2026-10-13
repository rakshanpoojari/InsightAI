import React from "react";
import { NavLink } from "react-router-dom";
import {
  Database,
  MessageSquareCode,
  LayoutDashboard,
  Sparkles,
  TrendingUp,
  LineChart,
  Settings,
  BrainCircuit,
} from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  tag?: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Upload & Profile", icon: Database },
  { to: "/chat", label: "AI Analytics Chat", icon: MessageSquareCode, tag: "NL→SQL" },
  { to: "/dashboard", label: "Executive Dashboard", icon: LayoutDashboard },
  { to: "/insights", label: "Evidence Insights", icon: Sparkles, tag: "AI" },
  { to: "/advanced", label: "Forecast & Anomalies", icon: TrendingUp },
  { to: "/cpi", label: "CPI Forecasting", icon: LineChart, tag: "NEW" },
  { to: "/settings", label: "System & Docs", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-slate-200 bg-white shadow-xs select-none">
      {/* Brand Header */}
      <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4.5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-700 to-indigo-500 text-white shadow-md shadow-brand-500/20">
          <BrainCircuit className="h-5 w-5" />
        </div>
        <div>
          <div className="text-base font-bold tracking-tight text-slate-900 flex items-center gap-1.5">
            InsightAI
            <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold text-brand-700 ring-1 ring-brand-200">
              v1.0
            </span>
          </div>
          <div className="text-xs text-slate-400">BI & Analytics Copilot</div>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 space-y-1.5 px-3 py-4 overflow-y-auto">
        <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Analytics Suite
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `group flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-brand-500 text-white shadow-sm shadow-brand-500/25"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`h-4 w-4 transition-colors ${
                        isActive ? "text-white" : "text-slate-400 group-hover:text-slate-600"
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>
                  {item.tag && (
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ${
                        isActive
                          ? "bg-white/20 text-white"
                          : "bg-slate-100 text-slate-500 group-hover:bg-slate-200/60"
                      }`}
                    >
                      {item.tag}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer / Engine Status */}
      <div className="border-t border-slate-100 p-4 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-medium text-slate-700">DuckDB & AI Engine Active</span>
        </div>
        <p className="text-[11px] text-slate-400 mt-0.5">Dual Mode: Heuristic + LLM ready</p>
      </div>
    </aside>
  );
}
