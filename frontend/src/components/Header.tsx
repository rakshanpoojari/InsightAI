import React from "react";
import { useDataset } from "../context/DatasetContext";
import { Database, CheckCircle2, AlertCircle } from "lucide-react";

export default function Header() {
  const { datasets, activeDataset, selectDataset, error, clearError } = useDataset();

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/95 px-6 backdrop-blur-md">
      {/* Active Dataset Display / Dropdown */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-brand-600" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Active Dataset:
          </span>
        </div>

        {datasets.length === 0 ? (
          <span className="text-sm font-medium text-slate-400">No datasets uploaded yet</span>
        ) : (
          <div className="relative">
            <select
              className="rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-3 pr-8 text-sm font-semibold text-slate-800 shadow-2xs hover:bg-white focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500 cursor-pointer"
              value={activeDataset?.id ?? ""}
              onChange={(e) => selectDataset(Number(e.target.value))}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.row_count.toLocaleString()} rows • {d.quality_score.toFixed(0)}% score)
                </option>
              ))}
            </select>
          </div>
        )}

        {activeDataset && (
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
            <CheckCircle2 className="h-3 w-3" />
            {activeDataset.status === "cleaned" ? "Cleaned & Profiled" : "Profiled"}
          </span>
        )}
      </div>

      {/* Global Error Banner if present */}
      {error && (
        <div className="absolute top-16 left-0 right-0 z-50 flex items-center justify-between bg-rose-50 border-b border-rose-200 px-6 py-2 text-xs font-medium text-rose-700">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
          <button onClick={clearError} className="font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}
    </header>
  );
}
