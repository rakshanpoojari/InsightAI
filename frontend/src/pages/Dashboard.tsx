import React, { useEffect, useState } from "react";
import { useDataset } from "../context/DatasetContext";
import { extractErrorMessage, getDashboard } from "../api/client";
import type { DashboardResponse } from "../types/dataset";
import ChartRenderer from "../components/ChartRenderer";
import { LoadingSpinner, SkeletonCard } from "../components/LoadingState";
import {
  LayoutDashboard,
  TrendingUp,
  DollarSign,
  Layers,
  ShieldCheck,
  BarChart,
  RefreshCw,
} from "lucide-react";

export default function Dashboard() {
  const { activeDataset, loadSample } = useDataset();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    if (!activeDataset) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await getDashboard(activeDataset.id);
      setData(res);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [activeDataset?.id]);

  if (!activeDataset) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <LayoutDashboard className="h-12 w-12 text-brand-500 mb-3" />
        <h2 className="text-lg font-bold text-slate-800">No Dataset Selected</h2>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Select or upload a dataset to generate an automated executive BI dashboard.
        </p>
        <button
          onClick={loadSample}
          className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 transition"
        >
          Load Sample Dataset
        </button>
      </div>
    );
  }

  const getKpiIcon = (category: string) => {
    switch (category) {
      case "revenue":
        return <DollarSign className="h-5 w-5 text-emerald-600" />;
      case "health":
        return <ShieldCheck className="h-5 w-5 text-brand-600" />;
      case "segment":
        return <Layers className="h-5 w-5 text-purple-600" />;
      default:
        return <TrendingUp className="h-5 w-5 text-blue-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Dashboard Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <LayoutDashboard className="h-6 w-6 text-brand-600" />
            Executive BI Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Automated KPI calculations, multi-dimensional breakdowns, and chronological trend charts for{" "}
            <strong className="text-slate-700">{activeDataset.name}</strong>.
          </p>
        </div>

        <button
          onClick={fetchDashboard}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <LoadingSpinner message="Calculating executive aggregations..." />
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Executive Summary Callout */}
          <div className="rounded-2xl border border-brand-100 bg-gradient-to-r from-brand-50/70 via-indigo-50/40 to-white p-5 shadow-2xs">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-xs shrink-0">
                <BarChart className="h-5 w-5" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-brand-700">
                  Automated Synthesis
                </div>
                <div className="text-sm font-medium text-slate-800 mt-1">
                  {data.summary}
                </div>
              </div>
            </div>
          </div>

          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {data.kpis.map((kpi) => (
              <div
                key={kpi.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs transition hover:shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {kpi.label}
                  </span>
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-50 border border-slate-100">
                    {getKpiIcon(kpi.category)}
                  </div>
                </div>
                <div className="mt-2 text-2xl font-black tracking-tight text-slate-900">
                  {kpi.value}
                </div>
                {kpi.subtitle && (
                  <div className="mt-1 text-xs text-slate-400 font-medium">
                    {kpi.subtitle}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {data.charts.map((chart) => (
              <div
                key={chart.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs transition hover:shadow-sm"
              >
                <div className="border-b border-slate-100 pb-3 mb-4">
                  <h3 className="text-sm font-bold text-slate-800">{chart.title}</h3>
                  {chart.description && (
                    <p className="text-xs text-slate-400 mt-0.5">{chart.description}</p>
                  )}
                </div>
                <ChartRenderer
                  type={chart.chart_type}
                  data={chart.data}
                  xKey={chart.x_key}
                  yKeys={chart.y_keys}
                  height={300}
                />
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
