import React, { useState, useEffect } from "react";
import { useDataset } from "../context/DatasetContext";
import {
  previewExecutiveReport,
  downloadExecutiveReportPdf,
  extractErrorMessage,
} from "../api/client";
import type {
  ReportGenerateRequest,
  ReportPreviewResponse,
  ReportSectionOptions,
} from "../types/dataset";
import { LoadingSpinner } from "../components/LoadingState";
import {
  FileText,
  Download,
  Eye,
  Sliders,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Compass,
  BarChart3,
  Lightbulb,
  ShieldCheck,
  TrendingUp,
  RefreshCw,
  FileSpreadsheet,
  Check,
} from "lucide-react";

const DEFAULT_SECTIONS: ReportSectionOptions = {
  executive_summary: true,
  data_health_audit: true,
  key_metrics_distribution: true,
  ai_insights: true,
  forecast_outlook: true,
  strategic_action_plan: true,
};

export default function ExecutiveReport() {
  const { activeDataset, loadSample } = useDataset();

  // Configuration Form State
  const [reportTitle, setReportTitle] = useState("Executive Business Intelligence Report");
  const [reportSubtitle, setReportSubtitle] = useState("");
  const [targetColumn, setTargetColumn] = useState("");
  const [dateColumn, setDateColumn] = useState("");
  const [horizon, setHorizon] = useState(14);
  const [sections, setSections] = useState<ReportSectionOptions>(DEFAULT_SECTIONS);

  // Status & Data
  const [preview, setPreview] = useState<ReportPreviewResponse | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const numericCols = activeDataset?.columns.filter((c) => c.inferred_type === "numeric") || [];
  const dateCols = activeDataset?.columns.filter((c) => c.inferred_type === "datetime") || [];

  useEffect(() => {
    if (activeDataset) {
      if (numericCols.length > 0 && !targetColumn) {
        setTargetColumn(numericCols[0].name);
      }
      if (dateCols.length > 0 && !dateColumn) {
        setDateColumn(dateCols[0].name);
      }
      setReportSubtitle(`Portfolio Performance & Predictive Strategy • ${activeDataset.name}`);
      // Load initial preview
      handleGeneratePreview(numericCols[0]?.name, dateCols[0]?.name);
    }
  }, [activeDataset?.id]);

  const buildRequestPayload = (overrideTarget?: string, overrideDate?: string): ReportGenerateRequest => {
    return {
      title: reportTitle.trim() || "Executive Business Intelligence Report",
      subtitle: reportSubtitle.trim() || undefined,
      target_column: overrideTarget || targetColumn || undefined,
      date_column: overrideDate || dateColumn || undefined,
      forecast_horizon: horizon,
      sections,
    };
  };

  const handleGeneratePreview = async (overrideTarget?: string, overrideDate?: string) => {
    if (!activeDataset) return;
    setIsLoadingPreview(true);
    setErrorMessage(null);
    try {
      const payload = buildRequestPayload(overrideTarget, overrideDate);
      const res = await previewExecutiveReport(activeDataset.id, payload);
      setPreview(res);
    } catch (e) {
      setErrorMessage(extractErrorMessage(e));
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!activeDataset) return;
    setIsDownloadingPdf(true);
    setErrorMessage(null);
    try {
      const payload = buildRequestPayload();
      const blob = await downloadExecutiveReportPdf(activeDataset.id, payload);

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const cleanName = activeDataset.name.replace(/[^a-zA-Z0-9_\-]/g, "_");
      link.download = `InsightAI_Executive_Report_${cleanName}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setErrorMessage(extractErrorMessage(e));
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const toggleSection = (key: keyof ReportSectionOptions) => {
    if (key === "executive_summary") return; // Always keep executive summary
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!activeDataset) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <FileText className="h-12 w-12 text-brand-500 mb-3" />
        <h2 className="text-lg font-bold text-slate-800">No Dataset Selected</h2>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Select or upload a dataset to generate a downloadable executive intelligence PDF report.
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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <FileText className="h-4 w-4" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              AI Executive Report Generator
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Synthesize verified data health, performance distributions, AI discoveries, and forecasts into a downloadable, presentation-ready PDF document.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => handleGeneratePreview()}
            disabled={isLoadingPreview}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-50 transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-brand-600 ${isLoadingPreview ? "animate-spin" : ""}`} />
            <span>{isLoadingPreview ? "Compiling..." : "Update Preview"}</span>
          </button>

          <button
            onClick={handleDownloadPdf}
            disabled={isDownloadingPdf}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 transition disabled:opacity-50"
          >
            {isDownloadingPdf ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-white" />
            ) : (
              <Download className="h-3.5 w-3.5 text-white" />
            )}
            <span>{isDownloadingPdf ? "Building PDF..." : "Download Executive PDF"}</span>
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="rounded-xl bg-rose-50 p-4 text-xs text-rose-700 ring-1 ring-rose-200 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Grid: Left Column Controls (4 cols) & Right Column Document Preview (8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Configuration Controls */}
        <div className="lg:col-span-4 space-y-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Sliders className="h-4 w-4 text-slate-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Report Configuration
              </h2>
            </div>

            {/* Title & Subtitle */}
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Document Title
                </label>
                <input
                  type="text"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-medium"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Document Subtitle
                </label>
                <input
                  type="text"
                  value={reportSubtitle}
                  onChange={(e) => setReportSubtitle(e.target.value)}
                  placeholder="e.g. Portfolio Performance Overview"
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-medium"
                />
              </div>
            </div>

            {/* Dimension Selectors */}
            <div className="space-y-3 border-t border-slate-100 pt-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Primary Metric Focus
                </label>
                <select
                  value={targetColumn}
                  onChange={(e) => setTargetColumn(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-semibold"
                >
                  {numericCols.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} (Numeric)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Date Dimension
                </label>
                <select
                  value={dateColumn}
                  onChange={(e) => setDateColumn(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-semibold"
                >
                  <option value="">Auto-Detect Temporal Sequence</option>
                  {activeDataset.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.inferred_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-700 mb-1">
                  <span>Forecast Horizon</span>
                  <span className="text-brand-600 font-black">{horizon} Periods</span>
                </div>
                <input
                  type="range"
                  min="3"
                  max="30"
                  step="1"
                  value={horizon}
                  onChange={(e) => setHorizon(parseInt(e.target.value))}
                  className="w-full accent-brand-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Section Toggles */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                Included Document Sections
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg bg-slate-50 text-xs text-slate-700 font-medium cursor-default">
                <span>Executive Summary & KPIs</span>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">Required</span>
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium cursor-pointer">
                <span>Data Health & Integrity Audit</span>
                <input
                  type="checkbox"
                  checked={sections.data_health_audit}
                  onChange={() => toggleSection("data_health_audit")}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium cursor-pointer">
                <span>Core Metric Distribution</span>
                <input
                  type="checkbox"
                  checked={sections.key_metrics_distribution}
                  onChange={() => toggleSection("key_metrics_distribution")}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium cursor-pointer">
                <span>AI Discovered Insights</span>
                <input
                  type="checkbox"
                  checked={sections.ai_insights}
                  onChange={() => toggleSection("ai_insights")}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium cursor-pointer">
                <span>Predictive Outlook & Forecast</span>
                <input
                  type="checkbox"
                  checked={sections.forecast_outlook}
                  onChange={() => toggleSection("forecast_outlook")}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium cursor-pointer">
                <span>Strategic Action Plan</span>
                <input
                  type="checkbox"
                  checked={sections.strategic_action_plan}
                  onChange={() => toggleSection("strategic_action_plan")}
                  className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
              </label>
            </div>
          </div>
        </div>

        {/* Right Column: Live Document Preview Canvas */}
        <div className="lg:col-span-8">
          {isLoadingPreview ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 shadow-xs">
              <LoadingSpinner message="Synthesizing multi-section verified analytics and generating executive report preview..." />
            </div>
          ) : preview ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm space-y-6">
              {/* Report Document Header */}
              <div className="border-b border-slate-200 pb-5 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-brand-700 bg-brand-50 border border-brand-100 px-2.5 py-0.5 rounded-full">
                    InsightAI Business Intelligence
                  </span>
                  <span className="text-[10px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                    Engine: {preview.narrative.ai_provider || "Gemini 2.5 Flash"}
                  </span>
                </div>

                <h2 className="text-xl font-black tracking-tight text-slate-900">
                  {preview.title}
                </h2>
                <p className="text-xs text-slate-500 font-medium">
                  {preview.subtitle}
                </p>

                <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-400">
                  <span>Scope: <strong>{preview.dataset_name}</strong></span>
                  <span>•</span>
                  <span>Audit Date: <strong>{new Date().toLocaleDateString()}</strong></span>
                  <span>•</span>
                  <span>Status: <strong className="text-emerald-600">Verified Calculations</strong></span>
                </div>
              </div>

              {/* Headline Stat Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 text-center">
                  <div className="text-lg font-black text-slate-900">
                    {preview.total_rows.toLocaleString()}
                  </div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">
                    Total Records
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 text-center">
                  <div className="text-lg font-black text-brand-700">
                    {preview.distribution.total !== undefined
                      ? preview.distribution.total > 1000
                        ? preview.distribution.total.toLocaleString(undefined, { maximumFractionDigits: 0 })
                        : preview.distribution.total.toFixed(2)
                      : "-"}
                  </div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5 truncate">
                    Total {preview.primary_metric || "Volume"}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 text-center">
                  <div className="text-lg font-black text-emerald-600">
                    {preview.quality_score.toFixed(1)}%
                  </div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">
                    Quality Health
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 text-center">
                  <div className="text-lg font-black text-slate-900">
                    {preview.forecast?.trend_direction || "Stable"}
                  </div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">
                    Trajectory
                  </div>
                </div>
              </div>

              {/* Executive Perspective Narrative */}
              {preview.narrative.executive_summary && (
                <div className="rounded-xl border border-brand-200 bg-brand-50/30 p-4 shadow-2xs space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-brand-700">
                    <Compass className="h-4 w-4 text-brand-600" />
                    <span>Executive Perspective</span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed font-medium">
                    {preview.narrative.executive_summary}
                  </p>
                </div>
              )}

              {/* Section 1: Data Health Audit */}
              {preview.sections.data_health_audit && (
                <div className="border-t border-slate-100 pt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      1. Data Health & Integrity Audit
                    </h3>
                    <span className="text-[11px] text-slate-500">
                      Quality Score: <strong>{preview.quality_score.toFixed(1)}%</strong>
                    </span>
                  </div>

                  {preview.quality_issues.length > 0 ? (
                    <div className="overflow-x-auto rounded-xl border border-slate-200">
                      <table className="min-w-full divide-y divide-slate-200 text-left text-[11px]">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-3 py-2 font-bold text-slate-700">Category</th>
                            <th className="px-3 py-2 font-bold text-slate-700">Severity</th>
                            <th className="px-3 py-2 font-bold text-slate-700">Column</th>
                            <th className="px-3 py-2 font-bold text-slate-700">Affected</th>
                            <th className="px-3 py-2 font-bold text-slate-700">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {preview.quality_issues.map((iss, i) => (
                            <tr key={i} className="hover:bg-slate-50/60">
                              <td className="px-3 py-1.5 font-medium text-slate-800 capitalize">
                                {iss.category.replace("_", " ")}
                              </td>
                              <td className="px-3 py-1.5">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                                    iss.severity === "high"
                                      ? "bg-rose-100 text-rose-800"
                                      : "bg-amber-100 text-amber-800"
                                  }`}
                                >
                                  {iss.severity}
                                </span>
                              </td>
                              <td className="px-3 py-1.5 text-slate-600 font-mono text-[10px]">
                                {iss.column || "Table-Wide"}
                              </td>
                              <td className="px-3 py-1.5 text-slate-600">
                                {iss.affected_rows_count.toLocaleString()} ({iss.affected_percentage.toFixed(1)}%)
                              </td>
                              <td className="px-3 py-1.5 text-slate-600 truncate max-w-xs">
                                {iss.recommended_action}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-3 bg-emerald-50 rounded-lg text-emerald-800 text-xs">
                      ✓ No critical data quality exceptions detected.
                    </div>
                  )}
                </div>
              )}

              {/* Section 2: Core Metric Distribution */}
              {preview.sections.key_metrics_distribution && preview.distribution && (
                <div className="border-t border-slate-100 pt-4 space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    2. Core Performance Distribution ({preview.primary_metric})
                  </h3>

                  <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-center text-xs">
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="block text-[10px] text-slate-400 font-bold uppercase">Total</span>
                      <strong className="text-slate-800 text-xs">
                        {preview.distribution.total?.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                      </strong>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="block text-[10px] text-slate-400 font-bold uppercase">Mean</span>
                      <strong className="text-slate-800 text-xs">
                        {preview.distribution.mean?.toFixed(2)}
                      </strong>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="block text-[10px] text-slate-400 font-bold uppercase">Median</span>
                      <strong className="text-slate-800 text-xs">
                        {preview.distribution.median?.toFixed(2)}
                      </strong>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="block text-[10px] text-slate-400 font-bold uppercase">Std Dev</span>
                      <strong className="text-slate-800 text-xs">
                        {preview.distribution.std?.toFixed(2)}
                      </strong>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="block text-[10px] text-slate-400 font-bold uppercase">Min</span>
                      <strong className="text-slate-800 text-xs">
                        {preview.distribution.min?.toFixed(2)}
                      </strong>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="block text-[10px] text-slate-400 font-bold uppercase">Max</span>
                      <strong className="text-slate-800 text-xs">
                        {preview.distribution.max?.toFixed(2)}
                      </strong>
                    </div>
                  </div>

                  {preview.top_categories && preview.top_categories.length > 0 && (
                    <div className="space-y-1.5 pt-2">
                      <span className="text-[11px] font-bold text-slate-600">Top Segment Contributors:</span>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                        {preview.top_categories.map((tc, idx) => (
                          <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="truncate font-medium text-slate-700">{tc.category}</span>
                            <span className="font-bold text-slate-900">{tc.value.toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Section 3: AI Discovered Insights */}
              {preview.sections.ai_insights && preview.insights && preview.insights.length > 0 && (
                <div className="border-t border-slate-100 pt-4 space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    3. AI Discovered Strategic Insights
                  </h3>
                  <div className="space-y-2">
                    {preview.insights.map((ins, idx) => (
                      <div key={idx} className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 space-y-1 text-xs">
                        <div className="flex items-center justify-between">
                          <strong className="text-slate-900">{ins.title}</strong>
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-brand-100 text-brand-800">
                            {ins.category}
                          </span>
                        </div>
                        <p className="text-slate-600 text-[11px]">{ins.description}</p>
                        {ins.recommendation && (
                          <div className="text-[11px] font-medium text-emerald-800 bg-white p-2 rounded border border-emerald-100">
                            Recommended: {ins.recommendation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Section 4: Predictive Forecast */}
              {preview.sections.forecast_outlook && preview.forecast && (
                <div className="border-t border-slate-100 pt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      4. Predictive Outlook ({preview.forecast.horizon} Periods)
                    </h3>
                    <span className="text-xs font-bold text-brand-700">
                      Trajectory: {preview.forecast.trend_direction} ({preview.forecast.expected_growth_pct > 0 ? "+" : ""}{preview.forecast.expected_growth_pct}%)
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    {preview.forecast.summary}
                  </p>

                  {preview.forecast.forecast_points && (
                    <div className="overflow-x-auto rounded-xl border border-slate-200">
                      <table className="min-w-full divide-y divide-slate-200 text-left text-[11px]">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-3 py-1.5 font-bold text-slate-700">Period</th>
                            <th className="px-3 py-1.5 font-bold text-slate-700">Predicted</th>
                            <th className="px-3 py-1.5 font-bold text-slate-700">Lower 95% Bound</th>
                            <th className="px-3 py-1.5 font-bold text-slate-700">Upper 95% Bound</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-mono">
                          {preview.forecast.forecast_points.map((pt, i) => (
                            <tr key={i} className="hover:bg-slate-50/60">
                              <td className="px-3 py-1.5 text-slate-700">{pt.date}</td>
                              <td className="px-3 py-1.5 text-brand-700 font-bold">{pt.predicted?.toLocaleString()}</td>
                              <td className="px-3 py-1.5 text-slate-500">{pt.lower_bound?.toLocaleString()}</td>
                              <td className="px-3 py-1.5 text-slate-500">{pt.upper_bound?.toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Section 5: Strategic Action Plan */}
              {preview.sections.strategic_action_plan && preview.narrative.action_plan && (
                <div className="border-t border-slate-100 pt-4 space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    5. Strategic Leadership Action Plan
                  </h3>
                  <div className="space-y-2">
                    {preview.narrative.action_plan.map((item, idx) => (
                      <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl border border-slate-200 bg-white shadow-2xs text-xs">
                        <div className="space-y-0.5">
                          <span className="font-bold text-brand-700 text-[11px] block">{item.timeframe}</span>
                          <span className="text-slate-800 font-medium">{item.action}</span>
                        </div>
                        <div className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-1 rounded border border-emerald-100 shrink-0">
                          {item.impact}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
