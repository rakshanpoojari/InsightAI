import React, { useState } from "react";
import {
  extractErrorMessage,
  previewDataset,
  uploadDataset,
} from "../api/client";
import { useDataset } from "../context/DatasetContext";
import type { DatasetPreview } from "../types/dataset";
import QualityScore from "../components/QualityScore";
import ColumnProfileTable from "../components/ColumnProfileTable";
import DataPreview from "../components/DataPreview";
import AIDataCleaningStudio from "../components/AIDataCleaningStudio";
import { LoadingSpinner } from "../components/LoadingState";
import {
  UploadCloud,
  FileSpreadsheet,
  Wand2,
  Trash2,
  FileText,
  Table as TableIcon,
} from "lucide-react";

export default function UploadExplore() {
  const {
    datasets,
    activeDataset,
    selectDataset,
    loadSample,
    deleteDatasetById,
    setActiveDatasetDetail,
    refreshDatasets,
    isLoading: isGlobalLoading,
  } = useDataset();

  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [activeTab, setActiveTab] = useState<"profile" | "preview" | "clean">("profile");
  const [localError, setLocalError] = useState<string | null>(null);

  // Load preview when activeDataset changes
  React.useEffect(() => {
    if (activeDataset) {
      previewDataset(activeDataset.id)
        .then(setPreview)
        .catch((e) => setLocalError(extractErrorMessage(e)));
    } else {
      setPreview(null);
    }
  }, [activeDataset]);

  async function handleUpload(file: File) {
    setLocalError(null);
    setIsUploading(true);
    try {
      const detail = await uploadDataset(file);
      await refreshDatasets();
      await selectDataset(detail.id);
    } catch (e) {
      setLocalError(extractErrorMessage(e));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Data Foundation & Ingestion
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Upload CSV/Excel spreadsheets, inspect inferred data profiles, clean missing values, and monitor quality scores.
          </p>
        </div>

        <button
          onClick={loadSample}
          disabled={isGlobalLoading}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition disabled:opacity-50"
        >
          <FileSpreadsheet className="h-4 w-4 text-brand-600" />
          <span>Load Included Sales Dataset</span>
        </button>
      </div>

      {localError && (
        <div className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700 ring-1 ring-rose-200">
          {localError}
        </div>
      )}

      {/* Main Grid: Upload/Datasets (4 cols) & Detail View (8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Upload Dropzone & Dataset Selector */}
        <div className="lg:col-span-4 space-y-5">
          <UploadDropzone onUpload={handleUpload} isUploading={isUploading} />

          {/* Dataset Inventory Card */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 bg-slate-50/50">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Uploaded Datasets ({datasets.length})
              </span>
            </div>

            <div className="divide-y divide-slate-100 max-h-[380px] overflow-y-auto">
              {datasets.length === 0 ? (
                <div className="px-4 py-8 text-center text-xs text-slate-400">
                  No datasets uploaded yet. Upload a CSV/Excel file or click "Load Included Sales Dataset".
                </div>
              ) : (
                datasets.map((d) => {
                  const isSelected = activeDataset?.id === d.id;
                  return (
                    <div
                      key={d.id}
                      onClick={() => selectDataset(d.id)}
                      className={`group flex items-center justify-between px-4 py-3 text-left transition cursor-pointer ${
                        isSelected
                          ? "bg-brand-50/70 border-l-4 border-brand-600"
                          : "hover:bg-slate-50"
                      }`}
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <div className="flex items-center gap-1.5 font-semibold text-sm text-slate-800 truncate">
                          <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <span className="truncate">{d.name}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {d.row_count.toLocaleString()} rows • {d.column_count} cols • {d.quality_score.toFixed(0)}% quality
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteDatasetById(d.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition shrink-0"
                        title="Delete dataset"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Profiling, Quality Score, Cleaning Studio & Preview */}
        <div className="lg:col-span-8 space-y-5">
          {!activeDataset ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
              <UploadCloud className="h-12 w-12 text-slate-300 mb-3" />
              <h3 className="text-base font-semibold text-slate-700">No Dataset Selected</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1 mb-4">
                Please upload a CSV or Excel file on the left, or select an existing dataset to review its profile and data quality.
              </p>
              <button
                onClick={loadSample}
                className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-700 transition"
              >
                Load Sample Dataset
              </button>
            </div>
          ) : (
            <>
              {/* Header Stats Bar */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2 flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Dataset Active
                    </div>
                    <div className="text-lg font-bold text-slate-900 truncate">
                      {activeDataset.name}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {activeDataset.row_count.toLocaleString()} rows • {activeDataset.column_count} columns • Ingested as {activeDataset.file_type.toUpperCase()}
                    </div>
                  </div>
                  <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700 ring-1 ring-brand-200">
                    {activeDataset.status}
                  </span>
                </div>

                <div className="md:col-span-1">
                  <QualityScore score={activeDataset.quality_score} />
                </div>
              </div>

              {/* Tabs Bar */}
              <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2">
                <button
                  onClick={() => setActiveTab("profile")}
                  className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition ${
                    activeTab === "profile"
                      ? "border-brand-600 text-brand-600"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <TableIcon className="h-4 w-4" />
                  <span>Column Profiles ({activeDataset.columns.length})</span>
                </button>

                <button
                  onClick={() => setActiveTab("preview")}
                  className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition ${
                    activeTab === "preview"
                      ? "border-brand-600 text-brand-600"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <FileText className="h-4 w-4" />
                  <span>Row Preview</span>
                </button>

                <button
                  onClick={() => setActiveTab("clean")}
                  className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition ${
                    activeTab === "clean"
                      ? "border-brand-600 text-brand-600"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <Wand2 className="h-4 w-4" />
                  <span>AI Data Cleaning Studio</span>
                </button>
              </div>

              {/* Tab Contents */}
              <div className="rounded-b-xl border-x border-b border-slate-200 bg-white p-5 shadow-xs">
                {activeTab === "profile" && (
                  <ColumnProfileTable columns={activeDataset.columns} />
                )}

                {activeTab === "preview" && (
                  preview ? (
                    <DataPreview preview={preview} />
                  ) : (
                    <LoadingSpinner message="Loading dataset preview..." />
                  )
                )}

                {activeTab === "clean" && (
                  <AIDataCleaningStudio
                    dataset={activeDataset}
                    onDatasetUpdated={async (updated) => {
                      setActiveDatasetDetail(updated);
                      await refreshDatasets();
                      try {
                        const updatedPrev = await previewDataset(updated.id);
                        setPreview(updatedPrev);
                      } catch (e) {
                        console.error("Failed to refresh preview", e);
                      }
                    }}
                  />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function UploadDropzone({
  onUpload,
  isUploading,
}: {
  onUpload: (file: File) => void;
  isUploading: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onUpload(file);
      }}
      className={`relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
        isDragging
          ? "border-brand-500 bg-brand-50/80 scale-[1.01]"
          : "border-slate-300 bg-white hover:border-slate-400"
      }`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600 mb-3 shadow-2xs">
        <UploadCloud className="h-6 w-6" />
      </div>
      <p className="text-sm font-bold text-slate-800">Drop your CSV or Excel file here</p>
      <p className="text-xs text-slate-400 mt-1 mb-4">Supports .csv, .xlsx, .xls up to 50MB</p>

      <label className="cursor-pointer rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 transition disabled:opacity-50">
        {isUploading ? "Parsing & Ingesting..." : "Browse Files"}
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          disabled={isUploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
            e.target.value = "";
          }}
        />
      </label>
    </div>
  );
}
