import axios from "axios";
import type {
  AnomalyResponse,
  CleaningOptions,
  DashboardResponse,
  DatasetDetail,
  DatasetPreview,
  DatasetSummary,
  ForecastResponse,
  InsightsResponse,
  QueryResult,
  SystemStatusResponse,
  CpiOptionsResponse,
  CpiForecastResponse,
  CpiForecastRequest,
} from "../types/dataset";

const api = axios.create({ baseURL: "/api" });

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

export async function loadCpiSample(): Promise<DatasetDetail> {
  const { data } = await api.post<DatasetDetail>("/datasets/load-cpi-sample");
  return data;
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
