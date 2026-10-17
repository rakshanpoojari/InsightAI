import React from "react";
import type { ForecastExplanation } from "../types/dataset";
import {
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ShieldCheck,
  Compass,
  ArrowRight,
  RefreshCw,
  BarChart3,
} from "lucide-react";

interface Props {
  explanation?: ForecastExplanation | null;
  isLoading?: boolean;
  onRefresh?: () => void;
  title?: string;
  isCpi?: boolean;
}

export default function AIForecastExplainer({
  explanation,
  isLoading = false,
  onRefresh,
  title = "AI Forecast Insights & Executive Explainer",
  isCpi = false,
}: Props) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-brand-200 bg-brand-50/20 p-6 shadow-xs flex items-center justify-center gap-3 text-brand-700">
        <RefreshCw className="h-5 w-5 animate-spin" />
        <span className="text-xs font-semibold">
          Synthesizing econometric forecast metrics and generating AI narrative...
        </span>
      </div>
    );
  }

  if (!explanation) {
    return null;
  }

  const isUpward = explanation.trend_direction.toLowerCase().includes("up");
  const isDownward = explanation.trend_direction.toLowerCase().includes("down");

  return (
    <div className="rounded-2xl border border-brand-200/90 bg-gradient-to-br from-white via-brand-50/15 to-white p-6 shadow-xs space-y-5">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-brand-100/70 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-xs">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">{title}</h3>
            <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
              <span>Model: <strong className="text-slate-700">{explanation.model_used}</strong></span>
              <span>•</span>
              <span>Confidence: <strong className="text-slate-700">{explanation.confidence_level}</strong></span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Trend Badge */}
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${
              isUpward
                ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
                : isDownward
                ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200"
                : "bg-slate-100 text-slate-700 ring-1 ring-slate-200"
            }`}
          >
            {isUpward ? (
              <TrendingUp className="h-3.5 w-3.5" />
            ) : isDownward ? (
              <TrendingDown className="h-3.5 w-3.5" />
            ) : (
              <Minus className="h-3.5 w-3.5" />
            )}
            <span>{explanation.trend_direction} ({explanation.projected_change_pct >= 0 ? "+" : ""}{explanation.projected_change_pct}%)</span>
          </span>

          {/* AI Provider Badge */}
          <span className="text-[10px] font-semibold text-brand-700 bg-brand-50 px-2 py-1 rounded-md border border-brand-200/60">
            {explanation.ai_provider || "Gemini 2.5 Flash"}
          </span>

          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-white rounded-lg border border-slate-200 transition shadow-2xs"
              title="Regenerate AI explanation"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Section 1: Executive Plain-Language Summary */}
      <div className="rounded-xl border border-brand-100 bg-white p-4 shadow-2xs space-y-1.5">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-brand-700">
          <Compass className="h-3.5 w-3.5" />
          <span>Executive Trajectory Summary</span>
        </div>
        <p className="text-xs text-slate-700 leading-relaxed font-medium">
          {explanation.summary}
        </p>
      </div>

      {/* Section 2: 3-Column Grid for Patterns, Assumptions, and Implications */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        {/* Historical Patterns */}
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
          <div className="flex items-center gap-1.5 font-bold text-slate-800">
            <BarChart3 className="h-3.5 w-3.5 text-brand-600" />
            <span>Historical Baseline & Rhythm</span>
          </div>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            {explanation.historical_patterns}
          </p>
        </div>

        {/* Assumptions & Uncertainty */}
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
          <div className="flex items-center gap-1.5 font-bold text-slate-800">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
            <span>Assumptions & Risk Variance</span>
          </div>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            {explanation.assumptions_uncertainty}
          </p>
        </div>

        {/* Business Implications */}
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
          <div className="flex items-center gap-1.5 font-bold text-slate-800">
            <Lightbulb className="h-3.5 w-3.5 text-emerald-600" />
            <span>{isCpi ? "Procurement & Pricing Impact" : "Business & Operational Impact"}</span>
          </div>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            {explanation.business_implications}
          </p>
        </div>
      </div>

      {/* Section 3: Concrete Actionable Recommendations */}
      {explanation.recommendations && explanation.recommendations.length > 0 && (
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4 space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-800">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>Prescribed Leadership Actions</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {explanation.recommendations.map((rec, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 bg-white p-3 rounded-lg border border-emerald-100 shadow-2xs text-[11px] text-slate-700"
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]">
                  {idx + 1}
                </span>
                <span className="leading-snug">{rec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
