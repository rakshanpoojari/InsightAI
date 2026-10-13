from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset, DatasetColumn
from app.schemas import DashboardChart, DashboardResponse, KPICard
from app.services.storage import read_dataframe


def _format_number(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"{val / 1_000:.1f}K"
    if isinstance(val, int) or val.is_integer():
        return f"{int(val):,}"
    return f"{val:.2f}"


def build_dashboard(engine: Engine, dataset: Dataset, columns: List[DatasetColumn]) -> DashboardResponse:
    df = read_dataframe(engine, dataset.storage_table_name)

    kpis: List[KPICard] = []
    charts: List[DashboardChart] = []

    num_cols = [c.name for c in columns if c.inferred_type == "numeric"]
    cat_cols = [c.name for c in columns if c.inferred_type == "categorical"]
    date_cols = [c.name for c in columns if c.inferred_type == "datetime"]

    # 1. Base KPI: Total Records
    kpis.append(
        KPICard(
            id="kpi-rows",
            label="Total Records",
            value=f"{len(df):,}",
            numeric_value=float(len(df)),
            subtitle=f"{len(columns)} tracked columns",
            category="volume",
        )
    )

    # 2. Data Quality KPI
    kpis.append(
        KPICard(
            id="kpi-quality",
            label="Data Quality Score",
            value=f"{dataset.quality_score:.1f}%",
            numeric_value=dataset.quality_score,
            change_direction="up" if dataset.quality_score >= 80 else "neutral",
            subtitle="Completeness & consistency",
            category="health",
        )
    )

    # 3. Primary Numeric KPI (Sum & Avg)
    if num_cols:
        primary_num = num_cols[0]
        s = df[primary_num].dropna()
        if not s.empty:
            total_val = float(s.sum())
            avg_val = float(s.mean())

            prefix = "$" if any(term in primary_num.lower() for term in ["sale", "profit", "price", "revenue", "cost"]) else ""
            kpis.append(
                KPICard(
                    id="kpi-total-primary",
                    label=f"Total {primary_num}",
                    value=f"{prefix}{_format_number(total_val)}",
                    numeric_value=total_val,
                    subtitle=f"Aggregated sum of {primary_num}",
                    category="revenue",
                )
            )
            kpis.append(
                KPICard(
                    id="kpi-avg-primary",
                    label=f"Avg {primary_num}",
                    value=f"{prefix}{_format_number(avg_val)}",
                    numeric_value=avg_val,
                    subtitle=f"Per-record average",
                    category="average",
                )
            )

    # 4. Dimension Cardinality KPI
    if cat_cols:
        primary_cat = cat_cols[0]
        unique_cnt = df[primary_cat].nunique()
        kpis.append(
            KPICard(
                id="kpi-cardinality",
                label=f"Active {primary_cat}s",
                value=f"{unique_cnt:,}",
                numeric_value=float(unique_cnt),
                subtitle=f"Unique segments tracked",
                category="segment",
            )
        )

    # Chart 1: Time Series / Trend if Date column exists
    if date_cols and num_cols:
        date_col = date_cols[0]
        primary_num = num_cols[0]
        # Group by date
        df_time = (
            df[[date_col, primary_num]]
            .dropna()
            .groupby(date_col)[primary_num]
            .sum()
            .reset_index()
            .sort_values(by=date_col)
            .head(30)
        )
        data_points = [
            {"date": str(row[date_col]), primary_num: round(float(row[primary_num]), 2)}
            for _, row in df_time.iterrows()
        ]
        charts.append(
            DashboardChart(
                id="chart-trend",
                title=f"{primary_num} Over Time",
                chart_type="area",
                x_key="date",
                y_keys=[primary_num],
                data=data_points,
                description=f"Chronological trajectory of {primary_num} across dates.",
            )
        )

    # Chart 2: Categorical Breakdown (Top Categories)
    if cat_cols and num_cols:
        primary_cat = cat_cols[0]
        primary_num = num_cols[0]
        df_cat = (
            df[[primary_cat, primary_num]]
            .dropna()
            .groupby(primary_cat)[primary_num]
            .sum()
            .reset_index()
            .sort_values(by=primary_num, ascending=False)
            .head(10)
        )
        data_points = [
            {"name": str(row[primary_cat]), primary_num: round(float(row[primary_num]), 2)}
            for _, row in df_cat.iterrows()
        ]
        charts.append(
            DashboardChart(
                id="chart-category-bar",
                title=f"Top {primary_cat}s by {primary_num}",
                chart_type="bar",
                x_key="name",
                y_keys=[primary_num],
                data=data_points,
                description=f"Performance breakdown ranking top {primary_cat} segments.",
            )
        )

    # Chart 3: Donut / Pie Share for secondary or primary category
    if cat_cols and num_cols:
        cat_for_pie = cat_cols[1] if len(cat_cols) > 1 else cat_cols[0]
        primary_num = num_cols[0]
        df_pie = (
            df[[cat_for_pie, primary_num]]
            .dropna()
            .groupby(cat_for_pie)[primary_num]
            .sum()
            .reset_index()
            .sort_values(by=primary_num, ascending=False)
            .head(6)
        )
        data_points = [
            {"name": str(row[cat_for_pie]), "value": round(float(row[primary_num]), 2)}
            for _, row in df_pie.iterrows()
        ]
        charts.append(
            DashboardChart(
                id="chart-distribution-pie",
                title=f"{primary_num} Share by {cat_for_pie}",
                chart_type="pie",
                x_key="name",
                y_keys=["value"],
                data=data_points,
                description=f"Proportional distribution across key {cat_for_pie} cohorts.",
            )
        )

    # Chart 4: Multi-metric comparison (e.g. Sales vs Profit)
    if len(num_cols) >= 2 and cat_cols:
        num1 = num_cols[0]
        num2 = num_cols[1]
        primary_cat = cat_cols[0]
        df_multi = (
            df[[primary_cat, num1, num2]]
            .dropna()
            .groupby(primary_cat)[[num1, num2]]
            .sum()
            .reset_index()
            .sort_values(by=num1, ascending=False)
            .head(8)
        )
        data_points = [
            {
                "name": str(row[primary_cat]),
                num1: round(float(row[num1]), 2),
                num2: round(float(row[num2]), 2),
            }
            for _, row in df_multi.iterrows()
        ]
        charts.append(
            DashboardChart(
                id="chart-multi-comparison",
                title=f"{num1} vs {num2} by {primary_cat}",
                chart_type="bar",
                x_key="name",
                y_keys=[num1, num2],
                data=data_points,
                description=f"Side-by-side metric comparison across {primary_cat}.",
            )
        )

    summary = (
        f"Executive summary for dataset '{dataset.name}': {len(df):,} total records analyzed "
        f"with a quality score of {dataset.quality_score:.1f}%. "
        f"Contains {len(num_cols)} numerical dimensions and {len(cat_cols)} categorical fields."
    )

    return DashboardResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        kpis=kpis,
        charts=charts,
        summary=summary,
    )
