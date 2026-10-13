import React from "react";
import { Loader2 } from "lucide-react";

export function LoadingSpinner({ message = "Processing data..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-slate-500">
      <Loader2 className="h-8 w-8 animate-spin text-brand-600 mb-3" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm animate-pulse">
      <div className="h-4 w-1/3 rounded bg-slate-200 mb-3" />
      <div className="h-8 w-1/2 rounded bg-slate-200 mb-2" />
      <div className="h-3 w-2/3 rounded bg-slate-100" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm animate-pulse space-y-3">
      <div className="h-6 w-1/4 rounded bg-slate-200 mb-4" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="h-4 w-1/4 rounded bg-slate-100" />
          <div className="h-4 w-1/4 rounded bg-slate-100" />
          <div className="h-4 w-1/4 rounded bg-slate-100" />
          <div className="h-4 w-1/4 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}
