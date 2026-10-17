from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset, DatasetColumn
from app.schemas import ForecastPoint, ForecastRequest, ForecastResponse, ForecastExplanation
from app.services import gemini_service
from app.services.storage import read_dataframe


def run_forecast(
    engine: Engine,
    dataset: Dataset,
    columns: List[DatasetColumn],
    request: ForecastRequest,
) -> ForecastResponse:
    df = read_dataframe(engine, dataset.storage_table_name)
    if df.empty:
        raise ValueError("Dataset is empty.")

    num_cols = [c.name for c in columns if c.inferred_type == "numeric"]
    date_cols = [c.name for c in columns if c.inferred_type == "datetime"]

    if not num_cols:
        raise ValueError("Forecasting requires at least one numeric metric column.")

    target_col = request.target_column or num_cols[0]
    if target_col not in df.columns:
        target_col = num_cols[0]

    # Resolve date column
    date_col = request.date_column
    if not date_col or date_col not in df.columns:
        if date_cols:
            date_col = date_cols[0]
        else:
            # Check if any column can be coerced to datetime
            for c in df.columns:
                if c != target_col:
                    try:
                        parsed = pd.to_datetime(df[c], errors="coerce")
                        if parsed.notna().mean() > 0.6:
                            date_col = c
                            break
                    except Exception:
                        pass

    horizon = max(3, min(request.horizon, 60))

    if date_col:
        # Time-based aggregation
        df_clean = df[[date_col, target_col]].dropna().copy()
        df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors="coerce")
        df_clean[target_col] = pd.to_numeric(
            df_clean[target_col].astype(str).str.replace(",", "").str.strip(),
            errors="coerce"
        )
        df_clean = df_clean.dropna().sort_values(by=date_col)
        # Aggregate by date if multiple entries per day
        df_ts = df_clean.groupby(date_col)[target_col].sum().reset_index()
    else:
        # Fallback sequential sequence
        date_col = "Period"
        series_vals = pd.to_numeric(
            df[target_col].astype(str).str.replace(",", "").str.strip(),
            errors="coerce"
        ).dropna()
        df_ts = pd.DataFrame({
            date_col: [f"Period {i + 1}" for i in range(len(series_vals))],
            target_col: series_vals.values,
        })

    if len(df_ts) < 3:
        raise ValueError("At least 3 temporal points are required to generate a forecast model.")

    y = df_ts[target_col].astype(float).values
    x = np.arange(len(y))

    # Fit linear/trend model: y = mx + c
    slope, intercept = np.polyfit(x, y, 1)
    fitted_y = slope * x + intercept

    # Residuals & standard error of regression
    residuals = y - fitted_y
    std_err = np.std(residuals) if len(residuals) > 2 else (np.std(y) * 0.1 or 1.0)
    # 95% confidence interval multiplier ~ 1.96
    ci_margin = 1.96 * std_err

    # Compute R-squared
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = max(0.0, min(1.0, 1 - (ss_res / ss_tot))) if ss_tot > 0 else 0.0

    forecast_points: List[ForecastPoint] = []

    # 1. Historical points
    for i in range(len(y)):
        d_label = (
            df_ts[date_col].iloc[i].strftime("%Y-%m-%d")
            if hasattr(df_ts[date_col].iloc[i], "strftime")
            else str(df_ts[date_col].iloc[i])
        )
        pred_val = float(fitted_y[i])
        forecast_points.append(
            ForecastPoint(
                date=d_label,
                actual=round(float(y[i]), 2),
                predicted=round(pred_val, 2),
                lower_bound=round(max(0.0, pred_val - ci_margin), 2),
                upper_bound=round(pred_val + ci_margin, 2),
            )
        )

    # 2. Future points
    last_date = df_ts[date_col].iloc[-1] if hasattr(df_ts[date_col].iloc[-1], "strftime") else None
    freq_days = 1
    if last_date and len(df_ts) > 1:
        first_date = df_ts[date_col].iloc[0]
        span_days = max(1, (last_date - first_date).days)
        freq_days = max(1, span_days // len(df_ts))

    for h in range(1, horizon + 1):
        future_x = len(y) + h - 1
        future_pred = slope * future_x + intercept
        # Increasing uncertainty further into the future: CI widens with sqrt(h)
        scaled_margin = ci_margin * np.sqrt(1 + (h / len(y)))

        if last_date:
            future_date_obj = last_date + dt.timedelta(days=int(h * freq_days))
            future_date_label = future_date_obj.strftime("%Y-%m-%d")
        else:
            future_date_label = f"Period +{h}"

        forecast_points.append(
            ForecastPoint(
                date=future_date_label,
                actual=None,
                predicted=round(float(future_pred), 2),
                lower_bound=round(max(0.0, float(future_pred - scaled_margin)), 2),
                upper_bound=round(float(future_pred + scaled_margin), 2),
            )
        )

    avg_historical = float(np.mean(y))
    predicted_future_avg = float(np.mean([p.predicted for p in forecast_points[-horizon:]]))
    growth_rate = (
        ((predicted_future_avg - avg_historical) / avg_historical) * 100
        if avg_historical != 0
        else 0.0
    )
    trend_dir = "Upward" if slope > 0.05 else ("Downward" if slope < -0.05 else "Stable")

    metrics = {
        "trend_direction": trend_dir,
        "slope": round(float(slope), 3),
        "r_squared": round(float(r_squared), 3),
        "expected_growth_pct": round(float(growth_rate), 2),
        "avg_historical": round(avg_historical, 2),
        "projected_horizon_avg": round(predicted_future_avg, 2),
    }

    summary = (
        f"Generated {horizon}-period predictive forecast for '{target_col}' along '{date_col}'. "
        f"The series exhibits an {trend_dir.lower()} trend with an expected {growth_rate:+.1f}% shift "
        f"and model goodness-of-fit R² = {r_squared:.2f}."
    )

    forecast_info = {
        "dataset_name": dataset.name,
        "target_column": target_col,
        "date_column": str(date_col),
        "horizon": horizon,
        "trend_direction": trend_dir,
        "slope": round(float(slope), 3),
        "r_squared": round(float(r_squared), 3),
        "expected_growth_pct": round(float(growth_rate), 2),
        "avg_historical": round(avg_historical, 2),
        "projected_horizon_avg": round(predicted_future_avg, 2),
        "historical_points_count": len(y),
    }

    try:
        ai_expl_data = gemini_service.explain_forecast(forecast_info, is_cpi=False)
        ai_explanation = ForecastExplanation(**ai_expl_data)
    except Exception as e:
        ai_explanation = None

    return ForecastResponse(
        dataset_id=dataset.id,
        date_column=str(date_col),
        target_column=target_col,
        horizon=horizon,
        forecast_points=forecast_points,
        metrics=metrics,
        summary=summary,
        ai_explanation=ai_explanation,
    )
