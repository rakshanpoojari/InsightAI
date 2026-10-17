import datetime as dt
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


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


# ================= AI Data Cleaning Assistant Schemas =================
class QualityIssue(BaseModel):
    id: str
    category: str  # missing_values | duplicates | text_inconsistency | invalid_dates | numeric_formatting | outliers | invalid_values | type_inconsistency | calculation_anomaly
    severity: str  # high | medium | low
    column: Optional[str] = None
    affected_rows_count: int
    affected_percentage: float
    sample_values: List[str] = []
    title: str
    description: str
    why_it_matters: str
    recommended_action: str
    action_type: str
    expected_impact: str
    risks_assumptions: str
    is_selected_by_default: bool = True


class QualityReportResponse(BaseModel):
    dataset_id: int
    dataset_name: str
    total_rows: int
    total_columns: int
    quality_score: float
    issues_count_by_category: Dict[str, int]
    issues_count_by_severity: Dict[str, int]
    total_issues: int
    issues: List[QualityIssue]
    ai_summary: Optional[str] = None
    ai_provider: Optional[str] = None
    has_backup: bool = True


class CleanPreviewRequest(BaseModel):
    selected_issue_ids: List[str]


class CleanPreviewResponse(BaseModel):
    dataset_id: int
    rows_before: int
    rows_after: int
    current_quality_score: float
    projected_quality_score: float
    actions_to_apply: List[str]
    sample_before_rows: List[Dict[str, Any]]
    sample_after_rows: List[Dict[str, Any]]


class CleanApplyRequest(BaseModel):
    selected_issue_ids: List[str]
    confirm: bool = True


class CleanApplyResponse(BaseModel):
    dataset_id: int
    status: str
    rows_before: int
    rows_after: int
    old_quality_score: float
    new_quality_score: float
    actions_applied: List[str]
    applied_report: Dict[str, Any]
    summary: str


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
    ai_explanation: Optional[str] = None
    ai_supporting_figures: Optional[List[str]] = None
    ai_relevant_columns: Optional[List[str]] = None
    ai_insights: Optional[List[str]] = None
    ai_provider: Optional[str] = None


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
    affected_columns: Optional[List[str]] = None
    chart_preview: Optional[DashboardChart] = None


class InsightsResponse(BaseModel):
    dataset_id: int
    dataset_name: str
    insights: List[InsightCard]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    executive_summary: str
    ai_provider: Optional[str] = None
    ai_enhanced: bool = False


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


class ForecastExplanation(BaseModel):
    summary: str
    historical_patterns: str
    assumptions_uncertainty: str
    business_implications: str
    recommendations: List[str]
    model_used: str
    trend_direction: str
    projected_change_pct: float
    confidence_level: str
    ai_provider: Optional[str] = None


class ForecastResponse(BaseModel):
    dataset_id: int
    date_column: str
    target_column: str
    horizon: int
    forecast_points: List[ForecastPoint]
    metrics: Dict[str, Any]  # e.g., trend_direction, avg_growth, r_squared
    summary: str
    ai_explanation: Optional[ForecastExplanation] = None


# ================= Phase 3: Executive Report Generator schemas =================
class ReportSectionOptions(BaseModel):
    executive_summary: bool = True
    data_health_audit: bool = True
    key_metrics_distribution: bool = True
    ai_insights: bool = True
    forecast_outlook: bool = True
    strategic_action_plan: bool = True


class ReportGenerateRequest(BaseModel):
    title: Optional[str] = "Executive Business Intelligence Report"
    subtitle: Optional[str] = None
    target_column: Optional[str] = None
    date_column: Optional[str] = None
    forecast_horizon: int = 14
    sections: ReportSectionOptions = Field(default_factory=ReportSectionOptions)


class ReportPreviewResponse(BaseModel):
    title: str
    subtitle: str
    dataset_id: int
    dataset_name: str
    total_rows: int
    total_columns: int
    quality_score: float
    primary_metric: Optional[str] = None
    narrative: Dict[str, Any]
    distribution: Dict[str, Any]
    top_categories: List[Dict[str, Any]]
    quality_issues: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    forecast: Optional[Dict[str, Any]] = None
    sections: Dict[str, bool]

