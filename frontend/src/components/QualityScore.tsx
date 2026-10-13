import React from "react";
import { ShieldCheck, ShieldAlert, Sparkles } from "lucide-react";

interface Props {
  score: number;
}

export default function QualityScore({ score }: Props) {
  const isExcellent = score >= 85;
  const isModerate = score >= 60 && score < 85;

  const badgeColor = isExcellent
    ? "bg-emerald-50 text-emerald-700 ring-emerald-200 border-emerald-100"
    : isModerate
    ? "bg-amber-50 text-amber-700 ring-amber-200 border-amber-100"
    : "bg-rose-50 text-rose-700 ring-rose-200 border-rose-100";

  const barColor = isExcellent
    ? "bg-emerald-500"
    : isModerate
    ? "bg-amber-500"
    : "bg-rose-500";

  return (
    <div className={`rounded-xl border p-4 shadow-sm ${badgeColor}`}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/80 shadow-xs ring-1 ring-black/5">
            {isExcellent ? (
              <ShieldCheck className="h-6 w-6 text-emerald-600" />
            ) : isModerate ? (
              <Sparkles className="h-6 w-6 text-amber-600" />
            ) : (
              <ShieldAlert className="h-6 w-6 text-rose-600" />
            )}
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider opacity-75">
              Data Quality Score
            </div>
            <div className="text-xl font-black tracking-tight">{score.toFixed(1)}%</div>
          </div>
        </div>

        <div className="hidden sm:block text-right">
          <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-white/80 shadow-2xs">
            {isExcellent ? "Production Ready" : isModerate ? "Good Hygiene" : "Needs Cleaning"}
          </span>
          <div className="text-[11px] opacity-75 mt-0.5">Weighted metric health</div>
        </div>
      </div>

      <div className="mt-3 w-full bg-white/50 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}
