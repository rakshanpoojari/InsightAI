import React, { useState, useEffect } from "react";
import { useDataset } from "../context/DatasetContext";
import { askQuestion, extractErrorMessage, runRawQuery, getSuggestions } from "../api/client";
import type { QueryResult, ColumnProfile } from "../types/dataset";
import ChartRenderer from "../components/ChartRenderer";
import { LoadingSpinner } from "../components/LoadingState";
import {
  Send,
  Sparkles,
  Terminal,
  Copy,
  Check,
  Clock,
  Table as TableIcon,
  BarChart3,
  Lightbulb,
} from "lucide-react";

function buildFallbackSuggestions(columns: ColumnProfile[]): string[] {
  const nums = columns.filter((c) => c.inferred_type === "numeric");
  const cats = columns.filter((c) => c.inferred_type === "categorical" || c.inferred_type === "text");
  const dates = columns.filter(
    (c) =>
      c.inferred_type === "datetime" ||
      ["date", "month", "year", "time", "period"].some((k) => c.name.toLowerCase().includes(k))
  );

  const res: string[] = [];
  if (cats[0] && nums[0]) res.push(`Which ${cats[0].name} has the highest ${nums[0].name}?`);
  if (cats[1] && nums[1]) res.push(`What is the average ${nums[1].name} by ${cats[1].name}?`);
  else if (cats[0] && nums[0]) res.push(`Show ${nums[0].name} by ${cats[0].name}`);
  if (nums[0] && nums[1]) res.push(`What is the relationship between ${nums[0].name} and ${nums[1].name}?`);
  if (dates[0] && nums[0]) res.push(`Show ${nums[0].name} trends over ${dates[0].name}`);
  if (nums[0]) res.push(`What is the total ${nums[0].name}?`);
  res.push("What is the total number of records?");
  return Array.from(new Set(res)).slice(0, 6);
}

export default function ChatAnalytics() {
  const { activeDataset, loadSample } = useDataset();

  const [question, setQuestion] = useState("");
  const [activeTab, setActiveTab] = useState<"chat" | "sql">("chat");
  const [rawSql, setRawSql] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    if (!activeDataset) {
      setSuggestions([]);
      return;
    }
    // Set immediate schema-derived suggestions
    if (activeDataset.columns && activeDataset.columns.length > 0) {
      setSuggestions(buildFallbackSuggestions(activeDataset.columns));
    }
    // Fetch enriched suggestions from backend engine
    getSuggestions(activeDataset.id)
      .then((data) => {
        if (data && data.length > 0) {
          setSuggestions(data);
        }
      })
      .catch(() => {
        // Keep fallback
      });
  }, [activeDataset?.id]);

  const handleAsk = async (q: string) => {
    if (!activeDataset || !q.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await askQuestion(activeDataset.id, q);
      setResult(res);
      setRawSql(res.sql);
      setViewMode(res.chart_config ? "chart" : "table");
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSql = async () => {
    if (!activeDataset || !rawSql.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await runRawQuery(activeDataset.id, rawSql);
      setResult(res);
      setViewMode(res.chart_config ? "chart" : "table");
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setIsLoading(false);
    }
  };

  const copySql = () => {
    if (!result?.sql) return;
    navigator.clipboard.writeText(result.sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!activeDataset) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <Sparkles className="h-12 w-12 text-brand-500 mb-3" />
        <h2 className="text-lg font-bold text-slate-800">No Dataset Selected</h2>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Please upload or select a dataset first to start asking natural language questions and running analytics queries.
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-brand-600" />
            AI Analytics & NL-to-SQL Copilot
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Ask questions in plain English. InsightAI translates your question into validated DuckDB/SQL, executes it against real data, and generates interactive charts.
          </p>
        </div>

        {/* Tab switcher: Natural Language vs Direct SQL */}
        <div className="flex rounded-xl bg-slate-200/70 p-1">
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              activeTab === "chat"
                ? "bg-white text-slate-900 shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Sparkles className="h-3.5 w-3.5 text-brand-600" />
            <span>Ask Natural Question</span>
          </button>
          <button
            onClick={() => setActiveTab("sql")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              activeTab === "sql"
                ? "bg-white text-slate-900 shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Terminal className="h-3.5 w-3.5 text-slate-700" />
            <span>Direct SQL Console</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      {/* Query Input Box */}
      {activeTab === "chat" ? (
        <div className="space-y-3">
          <div className="relative flex items-center">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAsk(question)}
              placeholder="Ask anything about your data... e.g. 'What is the total sales by product?'"
              className="w-full rounded-2xl border border-slate-300 bg-white py-3.5 pl-4 pr-14 text-sm text-slate-900 placeholder-slate-400 shadow-xs focus:border-brand-500 focus:outline-hidden focus:ring-2 focus:ring-brand-500/20"
            />
            <button
              onClick={() => handleAsk(question)}
              disabled={isLoading || !question.trim()}
              className="absolute right-2.5 flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>

          {/* Prompt Chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-400 mr-1">
              <Lightbulb className="h-3 w-3 text-amber-500" />
              Suggested:
            </span>
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuestion(s);
                  handleAsk(s);
                }}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 shadow-2xs hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Direct SQL Editor */
        <div className="rounded-2xl border border-slate-200 bg-slate-900 p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono">SELECT Query Console (Read-only execution on table: {activeDataset.name})</span>
            <span className="text-[11px] text-slate-500">Only SELECT queries allowed</span>
          </div>
          <textarea
            rows={3}
            value={rawSql}
            onChange={(e) => setRawSql(e.target.value)}
            placeholder='SELECT "Product", SUM("Sales") AS Total_Sales FROM dataset GROUP BY "Product" ORDER BY Total_Sales DESC LIMIT 10'
            className="w-full rounded-xl bg-slate-950 p-3 font-mono text-xs text-emerald-400 placeholder-slate-600 border border-slate-800 focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
          />
          <div className="flex justify-end">
            <button
              onClick={handleRunSql}
              disabled={isLoading || !rawSql.trim()}
              className="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
            >
              <Terminal className="h-3.5 w-3.5" />
              <span>Run SQL Query</span>
            </button>
          </div>
        </div>
      )}

      {/* Query Result Section */}
      {isLoading ? (
        <LoadingSpinner message="Generating SQL & executing analytical query..." />
      ) : result ? (
        <div className="space-y-4">
          {/* AI Copilot Explanation Card (When Gemini is active) */}
          {result.ai_explanation && (
            <div className="rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50/70 via-white to-indigo-50/40 p-5 shadow-xs space-y-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-100/80 pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-white shadow-2xs">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">AI Copilot Analysis</h3>
                    <p className="text-[11px] text-slate-500">Verified factual explanation derived from query execution</p>
                  </div>
                </div>

                {result.ai_provider ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand-100/80 px-2.5 py-0.5 text-[11px] font-semibold text-brand-800 border border-brand-200">
                    <Sparkles className="h-3 w-3 text-brand-600" />
                    <span>{result.ai_provider}</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 border border-slate-200">
                    Deterministic Engine
                  </span>
                )}
              </div>

              {/* Narrative Answer */}
              <div className="text-sm leading-relaxed text-slate-800 font-medium">
                {result.ai_explanation}
              </div>

              {/* Verified Supporting Figures */}
              {result.ai_supporting_figures && result.ai_supporting_figures.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Verified Key Figures
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {result.ai_supporting_figures.map((fig, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-200/80"
                      >
                        {fig}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Strategic Insights & Hypotheses */}
              {result.ai_insights && result.ai_insights.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-slate-100">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                    <Lightbulb className="h-3 w-3 text-amber-500" />
                    Strategic Hypotheses & Insights
                  </div>
                  <ul className="space-y-1">
                    {result.ai_insights.map((ins, idx) => (
                      <li key={idx} className="text-xs text-slate-700 flex items-start gap-2">
                        <span className="text-brand-500 font-bold">•</span>
                        <span>{ins}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Referenced Columns */}
              {result.ai_relevant_columns && result.ai_relevant_columns.length > 0 && (
                <div className="flex items-center gap-2 text-[11px] text-slate-500 pt-1">
                  <span className="font-medium">Referenced Columns:</span>
                  <div className="flex flex-wrap gap-1">
                    {result.ai_relevant_columns.map((col) => (
                      <span key={col} className="font-mono rounded bg-white px-1.5 py-0.5 text-slate-700 border border-slate-200 text-[10px]">
                        {col}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* SQL Explanation & Timing Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200">
                  <Check className="h-3.5 w-3.5" />
                </span>
                <span className="text-sm font-bold text-slate-800">
                  {result.summary || "Query executed successfully"}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="h-3 w-3" />
                  {result.execution_time_ms} ms
                </span>
                <span>•</span>
                <span className="font-mono">{result.total_rows} row(s) returned</span>
              </div>
            </div>

            {/* Generated SQL snippet */}
            <div className="relative rounded-xl bg-slate-900 p-3 text-xs font-mono text-slate-100">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                Generated SQL
              </div>
              <code className="text-emerald-400 break-all">{result.sql}</code>
              <button
                onClick={copySql}
                className="absolute right-3 top-3 rounded-md bg-slate-800 p-1.5 text-slate-400 hover:text-white transition"
                title="Copy SQL"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>

            {/* Toggle view: Chart vs Table */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-1">
                <button
                  onClick={() => setViewMode("chart")}
                  className={`flex items-center gap-1 rounded-md px-3 py-1 text-xs font-semibold transition ${
                    viewMode === "chart"
                      ? "bg-white text-brand-700 shadow-2xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <BarChart3 className="h-3.5 w-3.5" />
                  <span>Chart View</span>
                </button>
                <button
                  onClick={() => setViewMode("table")}
                  className={`flex items-center gap-1 rounded-md px-3 py-1 text-xs font-semibold transition ${
                    viewMode === "table"
                      ? "bg-white text-brand-700 shadow-2xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <TableIcon className="h-3.5 w-3.5" />
                  <span>Data Table</span>
                </button>
              </div>
            </div>

            {/* View Mode: Chart */}
            {viewMode === "chart" && result.chart_config && (
              <div className="pt-2">
                <ChartRenderer
                  type={result.chart_config.chart_type}
                  data={result.rows}
                  xKey={result.chart_config.x_axis || result.columns[0]}
                  yKeys={
                    result.chart_config.series_keys.length > 0
                      ? result.chart_config.series_keys
                      : [result.columns[1]]
                  }
                  title={result.chart_config.title}
                  height={320}
                />
              </div>
            )}

            {/* View Mode: Table (or fallback if no chart) */}
            {(viewMode === "table" || !result.chart_config) && (
              <div className="max-h-80 overflow-auto rounded-xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                  <thead className="sticky top-0 bg-slate-50 font-semibold text-slate-700">
                    <tr>
                      {result.columns.map((col) => (
                        <th key={col} className="px-4 py-2 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {result.rows.map((r, i) => (
                      <tr key={i} className="hover:bg-slate-50">
                        {result.columns.map((c) => (
                          <td key={c} className="px-4 py-2 whitespace-nowrap text-slate-800">
                            {r[c] === null || r[c] === undefined
                              ? "—"
                              : typeof r[c] === "number"
                              ? (r[c] as number).toLocaleString(undefined, { maximumFractionDigits: 2 })
                              : String(r[c])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
