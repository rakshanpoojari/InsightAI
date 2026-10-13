import React, { useState, useMemo } from "react";
import type { DatasetPreview } from "../types/dataset";
import { Search, ChevronLeft, ChevronRight, Download } from "lucide-react";

export default function DataPreview({ preview }: { preview: DatasetPreview }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [pageSize, setPageSize] = useState(15);
  const [currentPage, setCurrentPage] = useState(1);

  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return preview.rows;
    const q = searchQuery.toLowerCase();
    return preview.rows.filter((row) =>
      preview.columns.some((col) => {
        const val = row[col];
        return val !== null && val !== undefined && String(val).toLowerCase().includes(q);
      })
    );
  }, [preview.rows, preview.columns, searchQuery]);

  const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
  const pageIndex = Math.min(currentPage, totalPages);
  const displayedRows = filteredRows.slice((pageIndex - 1) * pageSize, pageIndex * pageSize);

  const exportCSV = () => {
    if (!preview.columns.length || !preview.rows.length) return;
    const headers = preview.columns.join(",");
    const rows = preview.rows.map((r) =>
      preview.columns
        .map((c) => {
          const val = r[c];
          if (val === null || val === undefined) return '""';
          const str = String(val).replace(/"/g, '""');
          return `"${str}"`;
        })
        .join(",")
    );
    const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "insightai_preview_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-3">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search preview rows..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-9 pr-3 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>
            Showing <strong className="text-slate-800">{displayedRows.length}</strong> of{" "}
            <strong className="text-slate-800">{filteredRows.length}</strong> rows (Total:{" "}
            {preview.total_rows.toLocaleString()})
          </span>

          <button
            onClick={exportCSV}
            className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 font-medium text-slate-700 shadow-2xs hover:bg-slate-50 transition"
          >
            <Download className="h-3 w-3 text-slate-500" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="max-h-[420px] overflow-auto rounded-xl border border-slate-200 bg-white shadow-xs">
        <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
          <thead className="sticky top-0 z-10 bg-slate-50 text-slate-600 font-semibold shadow-2xs">
            <tr>
              <th className="w-12 px-3 py-2.5 text-center text-slate-400">#</th>
              {preview.columns.map((col) => (
                <th key={col} className="whitespace-nowrap px-4 py-2.5">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-normal">
            {displayedRows.length === 0 ? (
              <tr>
                <td colSpan={preview.columns.length + 1} className="py-8 text-center text-slate-400">
                  No matching records found in this preview.
                </td>
              </tr>
            ) : (
              displayedRows.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-3 py-2 text-center font-mono text-[11px] text-slate-400">
                    {(pageIndex - 1) * pageSize + i + 1}
                  </td>
                  {preview.columns.map((col) => {
                    const val = row[col];
                    const isNull = val === null || val === undefined;
                    return (
                      <td key={col} className="whitespace-nowrap px-4 py-2 text-slate-700">
                        {isNull ? (
                          <span className="rounded bg-slate-100 px-1 py-0.5 text-[10px] text-slate-400 italic">
                            null
                          </span>
                        ) : typeof val === "number" ? (
                          <span className="font-mono text-slate-800">{val.toLocaleString()}</span>
                        ) : (
                          String(val)
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="rounded border border-slate-200 bg-white px-2 py-0.5"
            >
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span>
              Page {pageIndex} of {totalPages}
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={pageIndex <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="rounded border border-slate-200 bg-white p-1 hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <button
                disabled={pageIndex >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="rounded border border-slate-200 bg-white p-1 hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
