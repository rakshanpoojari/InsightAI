import axios from "axios";
import type {
  AnomalyResponse,
  CleaningOptions,
  DashboardResponse,
  DatasetDetail,
  DatasetPreview,
  DatasetSummary,
  ForecastResponse,
  ForecastExplanation,
  InsightsResponse,
  QueryResult,
  SystemStatusResponse,
  CpiOptionsResponse,
  CpiForecastResponse,
  CpiForecastRequest,
  QualityReportResponse,
  CleanPreviewResponse,
  CleanApplyResponse,
  ReportGenerateRequest,
  ReportPreviewResponse,
} from "../types/dataset";

const api = axios.create({
  // VITE_API_BASE_URL is set in the Vercel frontend project's environment variables
  // to the backend origin, e.g. https://insightai-backend-six.vercel.app
  // All FastAPI routes are registered under /api/... so we append that here.
  // When not set (local dev), Vite's proxy forwards /api/* to localhost:8000.
  baseURL: `${(import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ""}/api`,
});

export async function uploadDataset(file: File): Promise<DatasetDetail> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<DatasetDetail>("/datasets/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function loadSampleDataset(): Promise<DatasetDetail> {
  const { data } = await api.post<DatasetDetail>("/datasets/load-sample");
  return data;
}

export async function listDatasets(): Promise<DatasetSummary[]> {
  const { data } = await api.get<DatasetSummary[]>("/datasets");
  return data;
}

export async function getDataset(id: number): Promise<DatasetDetail> {
  const { data } = await api.get<DatasetDetail>(`/datasets/${id}`);
  return data;
}

export async function previewDataset(id: number, limit = 50): Promise<DatasetPreview> {
  const { data } = await api.get<DatasetPreview>(`/datasets/${id}/preview`, { params: { limit } });
  return data;
}

export async function cleanDataset(id: number, options: CleaningOptions): Promise<DatasetDetail> {
  const { data } = await api.post<DatasetDetail>(`/datasets/${id}/clean`, options);
  return data;
}

export async function getQualityAudit(id: number): Promise<QualityReportResponse> {
  const { data } = await api.get<QualityReportResponse>(`/datasets/${id}/quality-audit`);
  return data;
}

export async function previewClean(id: number, selectedIssueIds: string[]): Promise<CleanPreviewResponse> {
  const { data } = await api.post<CleanPreviewResponse>(`/datasets/${id}/clean/preview`, {
    selected_issue_ids: selectedIssueIds,
  });
  return data;
}

export async function applyClean(id: number, selectedIssueIds: string[]): Promise<CleanApplyResponse> {
  const { data } = await api.post<CleanApplyResponse>(`/datasets/${id}/clean/apply`, {
    selected_issue_ids: selectedIssueIds,
    confirm: true,
  });
  return data;
}

export async function resetClean(id: number): Promise<DatasetDetail> {
  const { data } = await api.post<DatasetDetail>(`/datasets/${id}/clean/reset`);
  return data;
}

export function getExportUrl(id: number, format: "csv" | "xlsx"): string {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
  return `${base}/api/datasets/${id}/export?format=${format}`;
}

export async function deleteDataset(id: number): Promise<void> {
  await api.delete(`/datasets/${id}`);
}

// Phase 2: Analytics & SQL
export async function askQuestion(datasetId: number, question: string): Promise<QueryResult> {
  const { data } = await api.post<QueryResult>(`/datasets/${datasetId}/ask`, { question });
  return data;
}

export async function runRawQuery(datasetId: number, sql: string): Promise<QueryResult> {
  const { data } = await api.post<QueryResult>(`/datasets/${datasetId}/query`, { sql });
  return data;
}

export async function getSuggestions(datasetId: number): Promise<string[]> {
  const { data } = await api.get<string[]>(`/datasets/${datasetId}/suggestions`);
  return data;
}

// Phase 3: Dashboard
export async function getDashboard(datasetId: number): Promise<DashboardResponse> {
  const { data } = await api.get<DashboardResponse>(`/datasets/${datasetId}/dashboard`);
  return data;
}

// Phase 4: AI Insights
export async function getInsights(datasetId: number): Promise<InsightsResponse> {
  const { data } = await api.get<InsightsResponse>(`/datasets/${datasetId}/insights`);
  return data;
}

// Phase 5: Anomalies & Forecasting
export async function getAnomalies(
  datasetId: number,
  targetColumn?: string,
  contamination = 0.05
): Promise<AnomalyResponse> {
  const { data } = await api.post<AnomalyResponse>(`/datasets/${datasetId}/anomalies`, {
    target_column: targetColumn,
    contamination,
  });
  return data;
}

export async function getForecast(
  datasetId: number,
  targetColumn?: string,
  dateColumn?: string,
  horizon = 14
): Promise<ForecastResponse> {
  const { data } = await api.post<ForecastResponse>(`/datasets/${datasetId}/forecast`, {
    target_column: targetColumn,
    date_column: dateColumn,
    horizon,
  });
  return data;
}

export async function explainForecast(
  datasetId: number,
  targetColumn?: string,
  dateColumn?: string,
  horizon = 14
): Promise<ForecastExplanation> {
  const { data } = await api.post<ForecastExplanation>(`/datasets/${datasetId}/forecast/explain`, {
    target_column: targetColumn,
    date_column: dateColumn,
    horizon,
  });
  return data;
}

// Phase 6: CPI & Price Movement Forecasting
export async function getCpiOptions(datasetId: number): Promise<CpiOptionsResponse> {
  const { data } = await api.get<CpiOptionsResponse>(`/datasets/${datasetId}/cpi/options`);
  return data;
}

export async function getCpiForecast(
  datasetId: number,
  params: CpiForecastRequest
): Promise<CpiForecastResponse> {
  const { data } = await api.post<CpiForecastResponse>(`/datasets/${datasetId}/cpi/forecast`, params);
  return data;
}

export async function explainCpiForecast(
  datasetId: number,
  params: CpiForecastRequest
): Promise<ForecastExplanation> {
  const { data } = await api.post<ForecastExplanation>(`/datasets/${datasetId}/cpi/forecast/explain`, params);
  return data;
}

export async function loadCpiSample(): Promise<DatasetDetail> {
  const { data } = await api.post<DatasetDetail>("/datasets/load-cpi-sample");
  return data;
}

// Phase 7: AI Executive Report Generator
export async function previewExecutiveReport(
  datasetId: number,
  request: ReportGenerateRequest
): Promise<ReportPreviewResponse> {
  const { data } = await api.post<ReportPreviewResponse>(`/datasets/${datasetId}/report/preview`, request);
  return data;
}

export async function downloadExecutiveReportPdf(
  datasetId: number,
  request: ReportGenerateRequest
): Promise<Blob> {
  const response = await api.post(`/datasets/${datasetId}/report/pdf`, request, {
    responseType: "blob",
  });
  return response.data;
}

export async function getHealth(): Promise<Record<string, unknown>> {
  const { data } = await api.get<Record<string, unknown>>("/health");
  return data;
}

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  const { data } = await api.get<SystemStatusResponse>("/system/status");
  return data;
}

export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail ?? err.message;
  }
  return "An unexpected error occurred.";
}
