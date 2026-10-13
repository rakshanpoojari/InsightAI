import React, { useEffect, useState } from "react";
import { useDataset } from "../context/DatasetContext";
import { extractErrorMessage, getInsights } from "../api/client";
import type { InsightsResponse } from "../types/dataset";
import { LoadingSpinner, SkeletonCard } from "../components/LoadingState";
import {
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Lightbulb,
  Info,
  Network,
  RefreshCw,
  ArrowUpRight,
} from "lucide-react";

export default function Insights() {
  const { activeDataset, loadSample } = useDataset();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInsights = async () => {
    if (!activeDataset) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await getInsights(activeDataset.id);
      setData(res);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, [activeDataset?.id]);

  if (!activeDataset) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <Sparkles className="h-12 w-12 text-brand-500 mb-3" />
        <h2 className="text-lg font-bold text-slate-800">No Dataset Selected</h2>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Select or upload a dataset to generate evidence-based AI insights.
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

  const getCategoryTheme = (category: string) => {
    switch (category) {
      case "warning":
        return {
          icon: <AlertTriangle className="h-4 w-4 text-amber-600" />,
          badge: "bg-amber-50 text-amber-700 ring-amber-200 border-amber-200",
          border: "border-l-amber-500",
        };
      case "opportunity":
        return {
          icon: <Lightbulb className="h-4 w-4 text-emerald-600" />,
          badge: "bg-emerald-50 text-emerald-700 ring-emerald-200 border-emerald-200",
          border: "border-l-emerald-500",
        };
      case "trend":
        return {
          icon: <TrendingUp className="h-4 w-4 text-blue-600" />,
          badge: "bg-blue-50 text-blue-700 ring-blue-200 border-blue-200",
          border: "border-l-blue-500",
        };
      default:
        return {
          icon: <Info className="h-4 w-4 text-indigo-600" />,
          badge: "bg-indigo-50 text-indigo-700 ring-indigo-200 border-indigo-200",
          border: "border-l-indigo-500",
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-brand-600" />
            Evidence-Based AI Insights
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Statistical evidence synthesized into strategic findings: Pareto distribution, correlation drivers, volatility, and data health.
          </p>
        </div>

        <button
          onClick={fetchInsights}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Re-analyze Dataset</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <LoadingSpinner message="Synthesizing mathematical signals into strategic insights..." />
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Executive Summary Banner */}
          <div className="rounded-2xl border border-brand-100 bg-gradient-to-r from-brand-50/80 via-white to-slate-50 p-5 shadow-2xs">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-xs shrink-0">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-brand-700">
                  AI Strategic Synthesis
                </div>
                <div className="text-sm font-semibold text-slate-800 mt-1">
                  {data.executive_summary}
                </div>
              </div>
            </div>
          </div>

          {/* Insights Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {data.insights.map((card) => {
              const theme = getCategoryTheme(card.category);
              return (
                <div
                  key={card.id}
                  className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-xs border-l-4 ${theme.border} transition hover:shadow-sm space-y-3 flex flex-col justify-between`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {theme.icon}
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                          {card.category}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {card.metric && (
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs font-bold text-slate-800">
                            {card.metric}
                          </span>
                        )}
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${
                            card.impact === "high"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : card.impact === "medium"
                              ? "bg-amber-50 text-amber-700 border-amber-200"
                              : "bg-slate-50 text-slate-600 border-slate-200"
                          }`}
                        >
                          {card.impact} impact
                        </span>
                      </div>
                    </div>

                    <h3 className="text-base font-bold text-slate-900 mt-2">{card.title}</h3>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {card.description}
                    </p>
                  </div>

                  {card.recommendation && (
                    <div className="rounded-xl bg-slate-50 border border-slate-100 p-3 text-xs text-slate-700">
                      <div className="font-bold text-slate-800 flex items-center gap-1 mb-1">
                        <ArrowUpRight className="h-3.5 w-3.5 text-brand-600" />
                        Recommended Action:
                      </div>
                      <div>{card.recommendation}</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Correlation Matrix Heatmap */}
          {data.correlation_matrix && Object.keys(data.correlation_matrix).length > 1 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <Network className="h-4 w-4 text-brand-600" />
                <h3 className="text-sm font-bold text-slate-800">
                  Multivariate Correlation Matrix (Pearson r)
                </h3>
              </div>
              <p className="text-xs text-slate-500">
                Values range from -1.0 (inverse relationship) to +1.0 (direct relationship). Values near 0 indicate no linear correlation.
              </p>

              <div className="overflow-x-auto pt-2">
                <table className="min-w-full text-xs text-center border-collapse">
                  <thead>
                    <tr>
                      <th className="p-2.5 text-left font-bold text-slate-400">Metric</th>
                      {Object.keys(data.correlation_matrix).map((k) => (
                        <th key={k} className="p-2.5 font-semibold text-slate-700 whitespace-nowrap">
                          {k}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.correlation_matrix).map(([rowKey, cols]) => (
                      <tr key={rowKey} className="border-t border-slate-100">
                        <td className="p-2.5 text-left font-semibold text-slate-800 whitespace-nowrap">
                          {rowKey}
                        </td>
                        {Object.entries(cols).map(([colKey, val]) => {
                          const isSelf = rowKey === colKey;
                          const intensity = Math.abs(val);
                          let bg = "bg-white text-slate-600";
                          if (!isSelf) {
                            if (val > 0.6) bg = "bg-emerald-100 text-emerald-900 font-bold";
                            else if (val > 0.3) bg = "bg-emerald-50 text-emerald-800";
                            else if (val < -0.6) bg = "bg-rose-100 text-rose-900 font-bold";
                            else if (val < -0.3) bg = "bg-rose-50 text-rose-800";
                          }
                          return (
                            <td key={colKey} className={`p-2.5 font-mono ${bg}`}>
                              {isSelf ? "1.00" : val.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
