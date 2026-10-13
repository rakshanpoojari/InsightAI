import React, { useState, useMemo } from "react";
import type { ColumnProfile } from "../types/dataset";
import { Search, ChevronDown, ChevronUp, BarChart2 } from "lucide-react";

const typeBadge: Record<string, string> = {
  numeric: "bg-blue-50 text-blue-700 ring-blue-200 border-blue-200",
  categorical: "bg-purple-50 text-purple-700 ring-purple-200 border-purple-200",
  datetime: "bg-teal-50 text-teal-700 ring-teal-200 border-teal-200",
  boolean: "bg-orange-50 text-orange-700 ring-orange-200 border-orange-200",
  text: "bg-slate-100 text-slate-700 ring-slate-200 border-slate-200",
};

export default function ColumnProfileTable({ columns }: { columns: ColumnProfile[] }) {
  const [search, setSearch] = useState("");
  const [expandedCol, setExpandedCol] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!search.trim()) return columns;
    const q = search.toLowerCase();
    return columns.filter(
      (c) => c.name.toLowerCase().includes(q) || c.inferred_type.toLowerCase().includes(q)
    );
  }, [columns, search]);

  const toggleExpand = (colName: string) => {
    setExpandedCol(expandedCol === colName ? null : colName);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search columns or types..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-9 pr-3 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
          />
        </div>
        <span className="text-xs text-slate-400">
          {filtered.length} of {columns.length} columns
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
        <table className="min-w-full divide-y divide-slate-200 text-xs">
          <thead className="bg-slate-50 text-slate-600 font-semibold">
            <tr>
              <th className="px-4 py-2.5 text-left">Column Name</th>
              <th className="px-4 py-2.5 text-left">Semantic Type</th>
              <th className="px-4 py-2.5 text-left">Missing Values</th>
              <th className="px-4 py-2.5 text-left">Unique Values</th>
              <th className="px-4 py-2.5 text-left">Sample Values</th>
              <th className="px-4 py-2.5 text-center">Stats</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-normal">
            {filtered.map((col) => {
              const isExpanded = expandedCol === col.name;
              const hasStats = Object.keys(col.stats || {}).length > 0;

              return (
                <React.Fragment key={col.name}>
                  <tr className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-900">{col.name}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 border ${
                          typeBadge[col.inferred_type] || typeBadge.text
                        }`}
                      >
                        {col.inferred_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className={col.missing_count > 0 ? "text-amber-600 font-medium" : "text-slate-600"}>
                          {col.missing_count} ({col.missing_pct}%)
                        </span>
                        {col.missing_pct > 0 && (
                          <div className="w-12 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-amber-500 h-full rounded-full"
                              style={{ width: `${Math.min(100, col.missing_pct)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-slate-600 font-mono">
                      {col.unique_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 max-w-xs truncate">
                      {col.sample_values && col.sample_values.length > 0
                        ? col.sample_values.slice(0, 3).map(String).join(", ") +
                          (col.sample_values.length > 3 ? "…" : "")
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {hasStats ? (
                        <button
                          onClick={() => toggleExpand(col.name)}
                          className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-100 transition"
                        >
                          <BarChart2 className="h-3 w-3 text-brand-600" />
                          <span>{isExpanded ? "Hide" : "View"}</span>
                          {isExpanded ? (
                            <ChevronUp className="h-3 w-3" />
                          ) : (
                            <ChevronDown className="h-3 w-3" />
                          )}
                        </button>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                  </tr>

                  {/* Expanded Stats Row */}
                  {isExpanded && (
                    <tr className="bg-brand-50/30">
                      <td colSpan={6} className="px-6 py-3 border-y border-brand-100">
                        <div className="text-xs font-semibold text-brand-900 mb-2">
                          Detailed Metrics for "{col.name}" ({col.inferred_type})
                        </div>
                        {col.inferred_type === "numeric" ? (
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                            {["min", "max", "mean", "median", "std"].map((k) => (
                              <div key={k} className="rounded-lg bg-white p-2.5 border border-slate-200 shadow-2xs">
                                <div className="text-[10px] uppercase font-bold text-slate-400">{k}</div>
                                <div className="text-sm font-semibold text-slate-800 font-mono mt-0.5">
                                  {col.stats[k] !== undefined
                                    ? typeof col.stats[k] === "number"
                                      ? (col.stats[k] as number).toLocaleString(undefined, {
                                          maximumFractionDigits: 2,
                                        })
                                      : String(col.stats[k])
                                    : "—"}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : col.stats.top_values ? (
                          <div className="rounded-lg bg-white p-3 border border-slate-200 shadow-2xs">
                            <div className="text-[11px] font-bold text-slate-500 mb-2">
                              Top Observed Frequencies:
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(
                                col.stats.top_values as Record<string, number>
                              ).map(([val, count]) => (
                                <span
                                  key={val}
                                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-50 border border-slate-200 px-2 py-1 text-xs"
                                >
                                  <strong className="text-slate-700">{val}</strong>
                                  <span className="text-slate-400 font-mono">({count})</span>
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-slate-500 font-mono">
                            {JSON.stringify(col.stats)}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
