import datetime as dt
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    missing_count: int
    missing_pct: float
    unique_count: int
    sample_values: list[Any]
    stats: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class DatasetSummary(BaseModel):
    id: int
    name: str
    original_filename: str
    file_type: str
    row_count: int
    column_count: int
    quality_score: float
    status: str
    error_message: Optional[str] = None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetDetail(DatasetSummary):
    columns: list[ColumnProfile]


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int


class CleaningOptions(BaseModel):
    drop_duplicate_rows: bool = True
    fill_missing_numeric: str = "median"  # median | mean | zero | none
    fill_missing_categorical: str = "mode"  # mode | unknown | none
    trim_whitespace: bool = True


# ================= Phase 2: Analytics & SQL schemas =================
class RawQueryRequest(BaseModel):
    sql: str


class AskQuestionRequest(BaseModel):
    question: str


class ChartConfig(BaseModel):
    chart_type: str  # bar | line | area | pie | donut | metric
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    series_keys: List[str] = []
    title: str = ""
    description: Optional[str] = None


class QueryResult(BaseModel):
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    execution_time_ms: float
    chart_config: Optional[ChartConfig] = None
    summary: Optional[str] = None


# ================= Phase 3: Dashboard schemas =================
class KPICard(BaseModel):
    id: str
    label: str
    value: str
    numeric_value: Optional[float] = None
    change_direction: Optional[str] = None  # up | down | neutral
    subtitle: Optional[str] = None
    category: str = "metric"


class DashboardChart(BaseModel):
    id: str
    title: str
    chart_type: str
    x_key: str
    y_keys: List[str]
    data: List[Dict[str, Any]]
    description: Optional[str] = None


class DashboardResponse(BaseModel):
    dataset_id: int
    dataset_name: str
    kpis: List[KPICard]
    charts: List[DashboardChart]
    summary: str


# ================= Phase 4: AI Insights schemas =================
class InsightCard(BaseModel):
    id: str
    title: str
    category: str  # opportunity | warning | trend | info
    impact: str  # high | medium | low
    metric: Optional[str] = None
    description: str
    recommendation: Optional[str] = None
    chart_preview: Optional[DashboardChart] = None


class InsightsResponse(BaseModel):
    dataset_id: int
    dataset_name: str
    insights: List[InsightCard]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    executive_summary: str


# ================= Phase 5: Anomaly & Forecasting schemas =================
class AnomalyRequest(BaseModel):
    target_column: Optional[str] = None
    contamination: float = 0.05  # percentage expected anomalies (0.01 to 0.2)


class AnomalyPoint(BaseModel):
    index: int
    is_anomaly: bool
    score: float
    row: Dict[str, Any]
    reasons: List[str]


class AnomalyResponse(BaseModel):
    dataset_id: int
    target_column: str
    total_rows: int
    anomaly_count: int
    anomaly_pct: float
    chart_data: List[Dict[str, Any]]
    anomalies: List[AnomalyPoint]
    summary: str


class ForecastRequest(BaseModel):
    target_column: Optional[str] = None
    date_column: Optional[str] = None
    horizon: int = 14  # number of future periods to predict


class ForecastPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    predicted: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class ForecastResponse(BaseModel):
    dataset_id: int
    date_column: str
    target_column: str
    horizon: int
    forecast_points: List[ForecastPoint]
    metrics: Dict[str, Any]  # e.g., trend_direction, avg_growth, r_squared
    summary: str
