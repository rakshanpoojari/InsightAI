export interface ColumnProfile {
  name: string;
  inferred_type: "numeric" | "categorical" | "datetime" | "boolean" | "text";
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  sample_values: (string | number)[];
  stats: Record<string, unknown>;
}

export interface DatasetSummary {
  id: number;
  name: string;
  original_filename: string;
  file_type: string;
  row_count: number;
  column_count: number;
  quality_score: number;
  status: "uploaded" | "profiled" | "cleaned" | "error";
  error_message: string | null;
  created_at: string;
}

export interface DatasetDetail extends DatasetSummary {
  columns: ColumnProfile[];
}

export interface DatasetPreview {
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
}

export interface CleaningOptions {
  drop_duplicate_rows: boolean;
  fill_missing_numeric: "median" | "mean" | "zero" | "none";
  fill_missing_categorical: "mode" | "unknown" | "none";
  trim_whitespace: boolean;
}

// ================= Phase 2: Analytics Types =================
export interface ChartConfig {
  chart_type: "bar" | "line" | "area" | "pie" | "donut" | "metric";
  x_axis?: string;
  y_axis?: string;
  series_keys: string[];
  title: string;
  description?: string;
}

export interface QueryResult {
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
  execution_time_ms: number;
  chart_config?: ChartConfig;
  summary?: string;
}

// ================= Phase 3: Dashboard Types =================
export interface KPICard {
  id: string;
  label: string;
  value: string;
  numeric_value?: number;
  change_direction?: "up" | "down" | "neutral";
  subtitle?: string;
  category: string;
}

export interface DashboardChart {
  id: string;
  title: string;
  chart_type: "bar" | "line" | "area" | "pie";
  x_key: string;
  y_keys: string[];
  data: Record<string, unknown>[];
  description?: string;
}

export interface DashboardResponse {
  dataset_id: number;
  dataset_name: string;
  kpis: KPICard[];
  charts: DashboardChart[];
  summary: string;
}

// ================= Phase 4: AI Insights Types =================
export interface InsightCard {
  id: string;
  title: string;
  category: "opportunity" | "warning" | "trend" | "info";
  impact: "high" | "medium" | "low";
  metric?: string;
  description: string;
  recommendation?: string;
}

export interface InsightsResponse {
  dataset_id: number;
  dataset_name: string;
  insights: InsightCard[];
  correlation_matrix?: Record<string, Record<string, number>>;
  executive_summary: string;
}

// ================= Phase 5: Advanced Types =================
export interface AnomalyPoint {
  index: number;
  is_anomaly: boolean;
  score: number;
  row: Record<string, unknown>;
  reasons: string[];
}

export interface AnomalyResponse {
  dataset_id: number;
  target_column: string;
  total_rows: number;
  anomaly_count: number;
  anomaly_pct: number;
  chart_data: Record<string, unknown>[];
  anomalies: AnomalyPoint[];
  summary: string;
}

export interface ForecastPoint {
  date: string;
  actual?: number | null;
  predicted?: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
}

export interface ForecastResponse {
  dataset_id: number;
  date_column: string;
  target_column: string;
  horizon: number;
  forecast_points: ForecastPoint[];
  metrics: {
    trend_direction: string;
    slope: number;
    r_squared: number;
    expected_growth_pct: number;
    projected_horizon_avg: number;
  };
  summary: string;
}

export interface SystemStatusResponse {
  status: string;
  sqlite: {
    status: string;
    role: string;
    engine: string;
    database_file: string;
    file_size_bytes: number;
    file_size_formatted: string;
    total_tables: number;
    tables: string[];
  };
  duckdb: {
    status: string;
    role: string;
    version: string;
    capabilities: string[];
  };
  datasets_summary: {
    total_datasets: number;
    total_records: number;
    datasets: {
      id: number;
      name: string;
      storage_table_name: string;
      row_count: number;
      column_count: number;
      quality_score: number;
      status: string;
      created_at: string | null;
    }[];
  };
  environment: {
    python_version: string;
    api_service: string;
    ai_mode: string;
  };
}

// ================= CPI & Price Forecasting Types =================
export interface CpiPriceColumnOption {
  name: string;
  label: string;
  type: string;
}

export interface CpiOptionsResponse {
  supported: boolean;
  mode: "cpi" | "price_index" | "product_price" | "none";
  mode_label?: string;
  reason?: string;
  date_column?: string;
  price_column?: string;
  available_price_columns?: CpiPriceColumnOption[];
  dimension_columns?: string[];
  dimension_values?: Record<string, string[]>;
  categories?: string[];
  products?: string[];
  regions?: string[];
  min_date?: string;
  max_date?: string;
  total_observations?: number;
}

export interface CpiPoint {
  date: string;
  actual: number | null;
  predicted: number | null;
  lower_bound: number | null;
  upper_bound: number | null;
  is_forecast: boolean;
  is_anchor?: boolean;
}

export interface CpiForecastResponse {
  dataset_id: number;
  dataset_name: string;
  mode: "cpi" | "price_index" | "product_price" | "none";
  mode_label: string;
  unit_label?: string;
  date_column: string;
  price_column: string;
  dimension_column?: string;
  selected_dimension_value: string;
  horizon_months: number;
  forecast_start_date?: string;
  forecast_end_date?: string;
  current_index: number;
  forecasted_index: number;
  expected_change_pct: number;
  annualized_rate_pct: number;
  volatility_pct: number;
  historical_observations: number;
  model_name?: string;
  fit_rmse?: number;
  fit_mape?: number;
  is_constant_series?: boolean;
  highest_growth_category: string;
  lowest_growth_category: string;
  purchasing_recommendation: string;
  confidence_interval_note?: string;
  disclaimer: string;
  points: CpiPoint[];
}

export interface CpiForecastRequest {
  analysis_mode?: "auto" | "cpi" | "product_price" | "price_index";
  date_column?: string;
  price_column?: string;
  dimension_column?: string;
  dimension_value?: string;
  horizon_months?: number;
  start_date?: string;
  end_date?: string;
}



