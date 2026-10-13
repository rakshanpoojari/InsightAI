import React, { useEffect, useState } from "react";
import { getSystemStatus, extractErrorMessage } from "../api/client";
import { useDataset } from "../context/DatasetContext";
import type { SystemStatusResponse } from "../types/dataset";
import {
  Settings as SettingsIcon,
  CheckCircle2,
  Server,
  Database,
  Cpu,
  HelpCircle,
  FileSpreadsheet,
  RefreshCw,
  Zap,
  HardDrive,
  Layers,
  Table,
  Sparkles,
} from "lucide-react";

export default function Settings() {
  const { loadSample, isLoading: isGlobalLoading } = useDataset();
  const [statusData, setStatusData] = useState<SystemStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sampleLoadedNotice, setSampleLoadedNotice] = useState(false);

  const fetchStatus = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getSystemStatus();
      setStatusData(res);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleLoadSample = async () => {
    try {
      await loadSample();
      setSampleLoadedNotice(true);
      await fetchStatus();
      setTimeout(() => setSampleLoadedNotice(false), 4000);
    } catch {
      // Error handled in context
    }
  };

  return (
    <div className="max-w-5xl space-y-8 pb-12">
      {/* Header with Refresh Action */}
      <div className="border-b border-slate-200 pb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <SettingsIcon className="h-6 w-6 text-brand-600" />
            System Diagnostics & Architectural Settings
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time telemetry, storage catalog status, vectorized analytical engine, and operational guide.
          </p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={isLoading}
          className="inline-flex items-center gap-2 self-start sm:self-auto rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 text-slate-500 ${isLoading ? "animate-spin text-brand-600" : ""}`} />
          <span>{isLoading ? "Refreshing..." : "Refresh Status"}</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          Failed to load system diagnostics: {error}
        </div>
      )}

      {/* Real Architecture Status Cards (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. FastAPI API Service */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">API Service</span>
            <Server className="h-4 w-4 text-brand-600" />
          </div>
          <div>
            <div className="flex items-center gap-2 text-base font-bold text-slate-900">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>{statusData ? "FastAPI Online" : "Connecting..."}</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Python {statusData?.environment.python_version || "3.12+"} • Port 8000
            </div>
          </div>
          <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-2">
            RESTful Endpoints Active
          </div>
        </div>

        {/* 2. SQLite Persistent Storage */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Persistence Store</span>
            <Database className="h-4 w-4 text-indigo-600" />
          </div>
          <div>
            <div className="flex items-center gap-2 text-base font-bold text-slate-900">
              <span className="flex h-2.5 w-2.5 rounded-full bg-indigo-500" />
              <span>SQLite 3</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {statusData?.sqlite.file_size_formatted || "0 B"} • {statusData?.sqlite.total_tables || 0} Tables
            </div>
          </div>
          <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-2 truncate" title={statusData?.sqlite.database_file}>
            Catalog: {statusData?.sqlite.database_file || "insightai.db"}
          </div>
        </div>

        {/* 3. DuckDB Vectorized OLAP Engine */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Analytics Engine</span>
            <Zap className="h-4 w-4 text-amber-500" />
          </div>
          <div>
            <div className="flex items-center gap-2 text-base font-bold text-slate-900">
              <span className="flex h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span>DuckDB v{statusData?.duckdb.version || "1.1.1"}</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Vectorized In-Memory OLAP
            </div>
          </div>
          <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-2">
            Sub-millisecond Queries & CORR
          </div>
        </div>

        {/* 4. Intelligence Core */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Intelligence Core</span>
            <Cpu className="h-4 w-4 text-emerald-600" />
          </div>
          <div>
            <div className="flex items-center gap-2 text-base font-bold text-slate-900">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
              <span>Deterministic ML</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Scikit-Learn + NL Engine
            </div>
          </div>
          <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-2">
            IsolationForest & Regressors
          </div>
        </div>
      </div>

      {/* Storage vs Engine Clarity Banner */}
      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 font-bold text-indigo-950 text-sm">
            <Layers className="h-4 w-4 text-indigo-600" />
            Dual-Engine Data Architecture
          </div>
          <p className="text-xs text-indigo-800/80 leading-relaxed max-w-2xl">
            <strong>SQLite</strong> provides persistent metadata storage and isolated relational tables on disk, while{" "}
            <strong>DuckDB</strong> executes all aggregations, group-bys, and correlation queries using in-memory vectorized columnar execution.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100/80 px-3 py-1 text-xs font-semibold text-indigo-800">
            <HardDrive className="h-3.5 w-3.5" />
            Storage: SQLite
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100/80 px-3 py-1 text-xs font-semibold text-amber-900">
            <Zap className="h-3.5 w-3.5 text-amber-600" />
            Execution: DuckDB
          </span>
        </div>
      </div>

      {/* Live Physical Tables & Datasets Inspector */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Table className="h-5 w-5 text-brand-600" />
            <h2 className="text-base font-bold text-slate-800">
              Active Storage Catalog ({statusData?.sqlite.tables.length || 0} Tables)
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-medium">
            Total Records: {statusData?.datasets_summary.total_records.toLocaleString() || 0}
          </span>
        </div>

        {statusData?.datasets_summary.datasets && statusData.datasets_summary.datasets.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-600 font-bold">
                  <th className="py-2.5 px-3">Dataset Name</th>
                  <th className="py-2.5 px-3">Physical Storage Table</th>
                  <th className="py-2.5 px-3 text-right">Rows</th>
                  <th className="py-2.5 px-3 text-right">Columns</th>
                  <th className="py-2.5 px-3 text-center">Quality Score</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {statusData.datasets_summary.datasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-slate-50/60 transition">
                    <td className="py-2.5 px-3 font-semibold text-slate-800">{ds.name}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">{ds.storage_table_name}</td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-700">{ds.row_count.toLocaleString()}</td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-700">{ds.column_count}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full font-bold text-[10px] ${
                        ds.quality_score >= 85 ? "bg-emerald-100 text-emerald-800" :
                        ds.quality_score >= 70 ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-800"
                      }`}>
                        {ds.quality_score.toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="inline-block px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-medium capitalize">
                        {ds.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-slate-400">
            No datasets uploaded yet. Load the included sample dataset below or upload a file.
          </div>
        )}
      </div>

      {/* Sample Data Management */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <FileSpreadsheet className="h-5 w-5 text-brand-600" />
          <h2 className="text-base font-bold text-slate-800">
            Sample Business Dataset
          </h2>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          InsightAI includes a multi-dimensional retail and financial business dataset (
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700 font-mono">sales_sample.csv</code>
          ) containing categorical dimensions (Product, Region, Category, Customer), temporal dates,
          and numerical metrics (Sales, Profit, Units) with realistic null values for testing data profiling and cleaning.
        </p>

        <div className="flex items-center gap-3">
          <button
            onClick={handleLoadSample}
            disabled={isGlobalLoading || isLoading}
            className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
          >
            <FileSpreadsheet className="h-4 w-4" />
            <span>{isGlobalLoading ? "Loading Sample..." : "Load Included Sample Dataset (1-Click)"}</span>
          </button>
          {sampleLoadedNotice && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 animate-fade-in">
              <CheckCircle2 className="h-4 w-4" />
              Sample loaded & profiled successfully!
            </span>
          )}
        </div>
      </div>

      {/* Complete User Guide */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <HelpCircle className="h-5 w-5 text-brand-600" />
          <h2 className="text-base font-bold text-slate-800">
            How to Use InsightAI: Feature-by-Feature Guide
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1.5">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-[10px]">
                1
              </span>
              Upload & Profiling
            </div>
            <p className="text-slate-500 leading-relaxed">
              Upload any CSV or Excel file. The engine infers data types, detects missing values and unique counts, creates an isolated database table, and scores data quality.
            </p>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1.5">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-[10px]">
                2
              </span>
              Data Cleaning Studio
            </div>
            <p className="text-slate-500 leading-relaxed">
              Use deterministic imputation (median, mean, mode), drop duplicates, and trim whitespace to upgrade your Data Quality Score.
            </p>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1.5">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-[10px]">
                3
              </span>
              AI Analytics & NL-to-SQL
            </div>
            <p className="text-slate-500 leading-relaxed">
              Ask natural questions like <em>"What is the total revenue?"</em> or <em>"What is the correlation between sales and units?"</em>. The DuckDB engine executes safe SQL in milliseconds.
            </p>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1.5">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-[10px]">
                4
              </span>
              Executive Dashboards
            </div>
            <p className="text-slate-500 leading-relaxed">
              Automatic KPI cards (Total Records, Volume Sums, Cardinality) and multi-chart grids (Bar, Line, Area, Donut) ready for executive presentations.
            </p>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1.5">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-[10px]">
                5
              </span>
              Evidence-Based AI Insights
            </div>
            <p className="text-slate-500 leading-relaxed">
              Calculates Pareto concentration, volatility metrics, and Pearson correlation coefficients before generating actionable recommendations.
            </p>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4 space-y-1.5">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-100 text-brand-700 font-bold text-[10px]">
                6
              </span>
              Forecasts & Outlier Detection
            </div>
            <p className="text-slate-500 leading-relaxed">
              IsolationForest and Z-score outlier flagging alongside regression time-series forecasting with upper and lower 95% confidence bounds.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
