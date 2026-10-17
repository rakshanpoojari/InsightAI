import React, { useState, useEffect, useMemo } from "react";
import {
  getQualityAudit,
  previewClean,
  applyClean,
  resetClean,
  getExportUrl,
  extractErrorMessage,
} from "../api/client";
import type {
  DatasetDetail,
  QualityReportResponse,
  CleanPreviewResponse,
  CleanApplyResponse,
} from "../types/dataset";
import { LoadingSpinner } from "./LoadingState";
import {
  Wand2,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  RotateCcw,
  Download,
  Filter,
  Search,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  FileSpreadsheet,
  Check,
} from "lucide-react";

interface Props {
  dataset: DatasetDetail;
  onDatasetUpdated: (updated: DatasetDetail) => void;
}

export default function AIDataCleaningStudio({ dataset, onDatasetUpdated }: Props) {
  const [report, setReport] = useState<QualityReportResponse | null>(null);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [selectedIssueIds, setSelectedIssueIds] = useState<Set<string>>(new Set());

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [searchColumn, setSearchColumn] = useState<string>("");

  // Preview & Apply States
  const [previewData, setPreviewData] = useState<CleanPreviewResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [applyResult, setApplyResult] = useState<CleanApplyResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch quality audit on mount or dataset ID change
  const fetchAudit = async () => {
    setIsLoadingAudit(true);
    setErrorMsg(null);
    setPreviewData(null);
    setApplyResult(null);
    try {
      const data = await getQualityAudit(dataset.id);
      setReport(data);
      // Initialize selected issues with defaults
      const defaults = new Set<string>();
      data.issues.forEach((iss) => {
        if (iss.is_selected_by_default) {
          defaults.add(iss.id);
        }
      });
      setSelectedIssueIds(defaults);
    } catch (err) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsLoadingAudit(false);
    }
  };

  useEffect(() => {
    fetchAudit();
  }, [dataset.id]);

  // Filtered issues
  const filteredIssues = useMemo(() => {
    if (!report) return [];
    return report.issues.filter((iss) => {
      if (selectedCategory !== "all" && iss.category !== selectedCategory) return false;
      if (selectedSeverity !== "all" && iss.severity !== selectedSeverity) return false;
      if (
        searchColumn.trim() &&
        !(iss.column?.toLowerCase().includes(searchColumn.toLowerCase()) ||
          iss.title.toLowerCase().includes(searchColumn.toLowerCase()) ||
          iss.description.toLowerCase().includes(searchColumn.toLowerCase()))
      ) {
        return false;
      }
      return true;
    });
  }, [report, selectedCategory, selectedSeverity, searchColumn]);

  const toggleIssue = (id: string) => {
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllFiltered = () => {
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      filteredIssues.forEach((iss) => next.add(iss.id));
      return next;
    });
  };

  const deselectAllFiltered = () => {
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      filteredIssues.forEach((iss) => next.delete(iss.id));
      return next;
    });
  };

  // Preview clean
  const handlePreview = async () => {
    if (selectedIssueIds.size === 0) return;
    setIsPreviewing(true);
    setErrorMsg(null);
    try {
      const res = await previewClean(dataset.id, Array.from(selectedIssueIds));
      setPreviewData(res);
    } catch (err) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsPreviewing(false);
    }
  };

  // Apply clean
  const handleApply = async () => {
    if (selectedIssueIds.size === 0) return;
    const confirmMessage = `Apply ${selectedIssueIds.size} selected cleaning transformations to dataset "${dataset.name}"? A raw backup is preserved so you can revert at any time.`;
    if (!window.confirm(confirmMessage)) return;

    setIsApplying(true);
    setErrorMsg(null);
    try {
      const res = await applyClean(dataset.id, Array.from(selectedIssueIds));
      setApplyResult(res);
      setPreviewData(null);
      // Refetch audit and update active dataset detail
      const audit = await getQualityAudit(dataset.id);
      setReport(audit);
      onDatasetUpdated({
        ...dataset,
        quality_score: res.new_quality_score,
        row_count: res.rows_after,
      });
    } catch (err) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsApplying(false);
    }
  };

  // Reset to original
  const handleReset = async () => {
    if (!window.confirm("Revert this dataset to its original uploaded state? All cleaning transforms will be rolled back.")) {
      return;
    }
    setIsResetting(true);
    setErrorMsg(null);
    try {
      const restored = await resetClean(dataset.id);
      onDatasetUpdated(restored);
      await fetchAudit();
    } catch (err) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsResetting(false);
    }
  };

  if (isLoadingAudit) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Scanning dataset across 9 data quality dimensions & generating AI audit..." />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-6 text-center text-slate-500">
        <p>No data quality report available.</p>
        <button
          onClick={fetchAudit}
          className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-semibold"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Retry Scan
        </button>
      </div>
    );
  }

  const score = report.quality_score;
  const isHealthy = score >= 85;
  const isModerate = score >= 60 && score < 85;

  return (
    <div className="space-y-6">
      {/* Top Banner & Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Sparkles className="h-4 w-4" />
            </span>
            <h2 className="text-lg font-bold text-slate-900">AI Data Cleaning Studio</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Deterministic rule-based anomaly detection paired with Gemini AI plain-language explanations and safe reversible transformations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {report.has_backup && (
            <button
              onClick={handleReset}
              disabled={isResetting}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 transition disabled:opacity-50"
              title="Revert to original uploaded raw dataset"
            >
              <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? "animate-spin text-rose-600" : ""}`} />
              <span>{isResetting ? "Reverting..." : "Revert to Original"}</span>
            </button>
          )}

          <div className="inline-flex rounded-xl shadow-2xs">
            <a
              href={getExportUrl(dataset.id, "csv")}
              download
              className="inline-flex items-center gap-1.5 rounded-l-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition border-r-0"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              <span>Export CSV</span>
            </a>
            <a
              href={getExportUrl(dataset.id, "xlsx")}
              download
              className="inline-flex items-center gap-1.5 rounded-r-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
              <span>Export Excel</span>
            </a>
          </div>

          <button
            onClick={fetchAudit}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
            title="Re-run data quality scanner"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-xl bg-rose-50 p-3.5 text-xs text-rose-700 ring-1 ring-rose-200 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
          <div>{errorMsg}</div>
        </div>
      )}

      {/* Success Notification after Apply */}
      {applyResult && (
        <div className="rounded-xl bg-emerald-50 p-4 ring-1 ring-emerald-200 flex items-start gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs text-emerald-800 space-y-1">
            <p className="font-bold text-emerald-900">{applyResult.summary}</p>
            <p>
              Row count changed from {applyResult.rows_before.toLocaleString()} to{" "}
              {applyResult.rows_after.toLocaleString()}. Quality score improved from{" "}
              <span className="font-semibold">{applyResult.old_quality_score.toFixed(1)}%</span> to{" "}
              <span className="font-bold text-emerald-700">{applyResult.new_quality_score.toFixed(1)}%</span>.
            </p>
          </div>
        </div>
      )}

      {/* Quality Score Breakdown & Health Summary Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Score Card (5 cols) */}
        <div className="lg:col-span-5 rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50/50 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Data Quality Health
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  isHealthy
                    ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
                    : isModerate
                    ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                    : "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
                }`}
              >
                {isHealthy ? (
                  <>
                    <ShieldCheck className="h-3 w-3" /> Excellent
                  </>
                ) : isModerate ? (
                  <>
                    <Sparkles className="h-3 w-3" /> Moderate Risk
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-3 w-3" /> Critical Issues
                  </>
                )}
              </span>
            </div>

            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-4xl font-black tracking-tight text-slate-900">
                {score.toFixed(1)}%
              </span>
              <span className="text-xs text-slate-500">Overall Reliability</span>
            </div>

            {/* Progress bar */}
            <div className="mt-3 w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isHealthy ? "bg-emerald-500" : isModerate ? "bg-amber-500" : "bg-rose-500"
                }`}
                style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
              />
            </div>

            {/* Formula Explanation */}
            <div className="mt-4 border-t border-slate-100 pt-3">
              <div className="text-[11px] font-bold text-slate-600 mb-2">
                Weighted Quality Formula Breakdown:
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600">
                <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-100">
                  <span>Completeness:</span>
                  <span className="font-bold text-slate-800">35% weight</span>
                </div>
                <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-100">
                  <span>Uniqueness:</span>
                  <span className="font-bold text-slate-800">25% weight</span>
                </div>
                <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-100">
                  <span>Validity:</span>
                  <span className="font-bold text-slate-800">25% weight</span>
                </div>
                <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-100">
                  <span>Consistency:</span>
                  <span className="font-bold text-slate-800">15% weight</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>{report.total_rows.toLocaleString()} rows scanned</span>
            <span>{report.total_columns} columns analyzed</span>
            <span className="font-bold text-slate-700">{report.total_issues} issues detected</span>
          </div>
        </div>

        {/* Gemini AI Executive Summary Card (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl border border-brand-100 bg-brand-50/30 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-brand-700">
                <Sparkles className="h-4 w-4 text-brand-600" />
                <span>AI Data Health Assessment</span>
              </div>
              <span className="text-[10px] font-semibold text-slate-400 bg-white/80 px-2 py-0.5 rounded-md border border-brand-100">
                {report.ai_provider || "Gemini 2.5 Flash"}
              </span>
            </div>

            <div className="text-xs text-slate-700 leading-relaxed space-y-2 whitespace-pre-line bg-white/70 p-3.5 rounded-xl border border-brand-100/60 max-h-48 overflow-y-auto">
              {report.ai_summary || "No AI summary generated."}
            </div>
          </div>

          {/* Quick Severity Badges */}
          <div className="mt-4 pt-3 border-t border-brand-100/50 flex flex-wrap items-center gap-3 text-xs">
            <span className="text-slate-500 font-semibold">Severity Breakdown:</span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 font-bold text-[11px]">
              <AlertCircle className="h-3 w-3" />
              {report.issues_count_by_severity.high || 0} High
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[11px]">
              <AlertTriangle className="h-3 w-3" />
              {report.issues_count_by_severity.medium || 0} Medium
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-800 font-bold text-[11px]">
              <Info className="h-3 w-3" />
              {report.issues_count_by_severity.low || 0} Low
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Selection Controls */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Filter Issues ({filteredIssues.length} of {report.total_issues})
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={selectAllFiltered}
              className="px-2.5 py-1 text-xs font-semibold text-brand-600 hover:text-brand-800 hover:bg-brand-50 rounded-lg transition"
            >
              Select All Filtered
            </button>
            <span className="text-slate-300">|</span>
            <button
              onClick={deselectAllFiltered}
              className="px-2.5 py-1 text-xs font-semibold text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
            >
              Deselect All
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Category Dropdown */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800"
            >
              <option value="all">All Categories</option>
              <option value="missing_values">Missing Values</option>
              <option value="duplicate_rows">Duplicate Records</option>
              <option value="whitespace_casing">Whitespace & Casing</option>
              <option value="invalid_dates">Invalid Dates</option>
              <option value="localized_numbers">Localized / Currency Numbers</option>
              <option value="outliers">Statistical Outliers</option>
              <option value="invalid_values">Negative / Invalid Values</option>
              <option value="type_inconsistency">Type Inconsistency</option>
              <option value="calculation_anomaly">Calculation Inconsistencies</option>
            </select>
          </div>

          {/* Severity Dropdown */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Severity</label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800"
            >
              <option value="all">All Severities</option>
              <option value="high">High Severity</option>
              <option value="medium">Medium Severity</option>
              <option value="low">Low Severity</option>
            </select>
          </div>

          {/* Column / Keyword Search */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Search Column or Title</label>
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="e.g. Sales, Revenue, date..."
                value={searchColumn}
                onChange={(e) => setSearchColumn(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white pl-8 pr-2.5 py-1.5 text-xs text-slate-800 placeholder:text-slate-400"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Issues List */}
      <div className="space-y-3">
        {filteredIssues.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center text-xs text-slate-400">
            {report.total_issues === 0
              ? "No data quality issues detected! Dataset appears fully clean and production ready."
              : "No issues match the active filter criteria."}
          </div>
        ) : (
          filteredIssues.map((issue) => {
            const isChecked = selectedIssueIds.has(issue.id);
            const isHigh = issue.severity === "high";
            const isMedium = issue.severity === "medium";

            return (
              <div
                key={issue.id}
                className={`rounded-xl border transition p-4 ${
                  isChecked
                    ? "border-brand-300 bg-brand-50/20 shadow-xs"
                    : "border-slate-200 bg-white opacity-85 hover:opacity-100"
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleIssue(issue.id)}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                  />

                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Header Row */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            isHigh
                              ? "bg-rose-100 text-rose-800"
                              : isMedium
                              ? "bg-amber-100 text-amber-800"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {issue.severity}
                        </span>
                        <span className="text-xs font-bold text-slate-900">{issue.title}</span>
                        {issue.column && (
                          <span className="font-mono text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                            {issue.column}
                          </span>
                        )}
                      </div>

                      <div className="text-[11px] font-medium text-slate-500">
                        {issue.affected_rows_count.toLocaleString()} rows affected (
                        {issue.affected_percentage.toFixed(1)}%)
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-slate-600">{issue.description}</p>

                    {/* Sample Values if present */}
                    {issue.sample_values && issue.sample_values.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px] pt-1">
                        <span className="text-slate-400 font-medium">Sample problematic values:</span>
                        {issue.sample_values.map((val, idx) => (
                          <span
                            key={idx}
                            className="bg-slate-100 text-slate-800 font-mono px-1.5 py-0.5 rounded border border-slate-200"
                          >
                            {val}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* 2-Column Reasoning Block */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-[11px] border-t border-slate-100">
                      <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100 space-y-1">
                        <div className="font-bold text-slate-700 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3 text-amber-500" />
                          Why it matters & Business Risk:
                        </div>
                        <p className="text-slate-600">{issue.why_it_matters}</p>
                        {issue.risks_assumptions && (
                          <p className="text-slate-500 text-[10px] italic">
                            Assumption: {issue.risks_assumptions}
                          </p>
                        )}
                      </div>

                      <div className="bg-emerald-50/60 p-2.5 rounded-lg border border-emerald-100 space-y-1">
                        <div className="font-bold text-emerald-800 flex items-center gap-1">
                          <Wand2 className="h-3 w-3 text-emerald-600" />
                          Recommended Solution:
                        </div>
                        <p className="text-emerald-900">{issue.recommended_action}</p>
                        <p className="text-emerald-700 font-medium text-[10px]">
                          Expected Impact: {issue.expected_impact}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Preview & Apply Action Bar */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-slate-600">
          <span className="font-bold text-slate-800">{selectedIssueIds.size}</span> of{" "}
          <span className="font-bold text-slate-800">{report.issues.length}</span> issues selected
          for transformation.
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handlePreview}
            disabled={selectedIssueIds.size === 0 || isPreviewing}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-50 transition disabled:opacity-50"
          >
            {isPreviewing ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-brand-600" />
            ) : (
              <Wand2 className="h-3.5 w-3.5 text-brand-600" />
            )}
            <span>{isPreviewing ? "Calculating Preview..." : "Preview Proposed Changes"}</span>
          </button>

          <button
            onClick={handleApply}
            disabled={selectedIssueIds.size === 0 || isApplying}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 transition disabled:opacity-50"
          >
            {isApplying ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-white" />
            ) : (
              <Check className="h-3.5 w-3.5 text-white" />
            )}
            <span>{isApplying ? "Applying Pipeline..." : "Confirm & Apply Transforms"}</span>
          </button>
        </div>
      </div>

      {/* Preview Results Panel */}
      {previewData && (
        <div className="rounded-2xl border border-brand-200 bg-brand-50/20 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-white font-bold">
                <Wand2 className="h-4 w-4" />
              </span>
              <h3 className="text-sm font-bold text-slate-900">Transformation Sandbox Preview</h3>
            </div>
            <span className="text-xs font-medium text-brand-700 bg-brand-100/60 px-2.5 py-0.5 rounded-full">
              Non-destructive Simulation
            </span>
          </div>

          {/* Metric Comparison Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Row Count
              </div>
              <div className="mt-1 flex items-center gap-3">
                <span className="text-xl font-bold text-slate-700">
                  {previewData.rows_before.toLocaleString()}
                </span>
                <ArrowRight className="h-4 w-4 text-slate-400" />
                <span className="text-xl font-black text-brand-700">
                  {previewData.rows_after.toLocaleString()}
                </span>
                <span className="text-xs text-slate-500">
                  ({previewData.rows_after - previewData.rows_before >= 0 ? "+" : ""}
                  {(previewData.rows_after - previewData.rows_before).toLocaleString()} rows)
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Projected Quality Score
              </div>
              <div className="mt-1 flex items-center gap-3">
                <span className="text-xl font-bold text-slate-700">
                  {previewData.current_quality_score.toFixed(1)}%
                </span>
                <ArrowRight className="h-4 w-4 text-slate-400" />
                <span className="text-xl font-black text-emerald-600">
                  {previewData.projected_quality_score.toFixed(1)}%
                </span>
                <span className="text-xs text-emerald-600 font-semibold">
                  (+{(previewData.projected_quality_score - previewData.current_quality_score).toFixed(1)}% gain)
                </span>
              </div>
            </div>
          </div>

          {/* Actions to be applied */}
          <div>
            <div className="text-xs font-bold text-slate-800 mb-1.5">Actions Scheduled in Pipeline:</div>
            <div className="flex flex-wrap gap-1.5">
              {previewData.actions_to_apply.map((act, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded-md bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-2xs"
                >
                  <Check className="h-3 w-3 text-brand-600" />
                  {act}
                </span>
              ))}
            </div>
          </div>

          {/* Sample Rows Comparison Table */}
          {previewData.sample_after_rows && previewData.sample_after_rows.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-slate-800">
                Sample Transformed Rows Preview (First 5 Rows):
              </div>
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs max-h-56">
                <table className="min-w-full divide-y divide-slate-200 text-left text-[11px]">
                  <thead className="bg-slate-50 sticky top-0">
                    <tr>
                      {Object.keys(previewData.sample_after_rows[0] || {}).map((col) => (
                        <th key={col} className="px-3 py-2 font-bold text-slate-700 truncate">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {previewData.sample_after_rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-50/70">
                        {Object.keys(previewData.sample_after_rows[0] || {}).map((col) => (
                          <td key={col} className="px-3 py-1.5 text-slate-600 whitespace-nowrap">
                            {String(row[col] ?? "NULL")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
