from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset, DatasetColumn
from app.services.storage import read_dataframe

logger = logging.getLogger("insightai.cpi")


def detect_cpi_capabilities(
    engine: Engine,
    dataset: Dataset,
    columns: List[DatasetColumn],
) -> Dict[str, Any]:
    """
    Analyzes active dataset schema and content to determine if CPI or
    Price Index / Product Price forecasting is supported.
    Dynamically identifies date, price/index, and dimension columns.
    """
    df = read_dataframe(engine, dataset.storage_table_name)
    if df.empty:
        return {
            "supported": False,
            "reason": "Dataset contains no records.",
            "mode": "none",
            "date_column": None,
            "price_column": None,
            "available_price_columns": [],
            "dimension_columns": [],
            "dimension_values": {},
            "categories": [],
            "products": [],
            "regions": [],
            "min_date": None,
            "max_date": None,
            "total_observations": 0,
        }

    # 1. Detect Temporal Date Column
    date_col = None
    for c in columns:
        if c.inferred_type == "datetime":
            date_col = c.name
            break

    if not date_col:
        for col_name in df.columns:
            low = col_name.lower()
            if any(k in low for k in ["date", "month", "period", "timestamp", "year", "time"]):
                try:
                    parsed = pd.to_datetime(df[col_name], errors="coerce")
                    if parsed.notna().mean() > 0.5:
                        date_col = col_name
                        break
                except Exception:
                    pass

    # 2. Detect Price / CPI Metric Columns
    available_price_cols = []
    cpi_col = None
    unit_price_col = None
    price_index_col = None
    financial_col = None

    for col_name in df.columns:
        if col_name == date_col:
            continue
        low = col_name.lower()
        if "cpi" in low or "consumer_price_index" in low:
            cpi_col = cpi_col or col_name
            available_price_cols.append({
                "name": col_name,
                "label": "Consumer Price Index (CPI)",
                "type": "cpi",
            })
        elif "price_index" in low:
            price_index_col = price_index_col or col_name
            available_price_cols.append({
                "name": col_name,
                "label": "Price Index (Base = 100)",
                "type": "price_index",
            })
        elif any(k in low for k in ["unit_price", "price", "avg_price", "item_price", "rate"]):
            unit_price_col = unit_price_col or col_name
            available_price_cols.append({
                "name": col_name,
                "label": "Product Unit Price ($)",
                "type": "product_price",
            })
        elif any(k in low for k in ["sales", "revenue", "cost", "expense", "amount"]):
            financial_col = financial_col or col_name
            available_price_cols.append({
                "name": col_name,
                "label": f"Monetary Metric ({col_name})",
                "type": "product_price",
            })

    # Determine primary price column and default mode
    primary_price_col = cpi_col or unit_price_col or price_index_col or financial_col
    default_mode = "none"
    if cpi_col:
        default_mode = "cpi"
    elif unit_price_col:
        default_mode = "product_price"
    elif price_index_col:
        default_mode = "price_index"
    elif financial_col:
        default_mode = "price_index"

    if not date_col or not primary_price_col:
        return {
            "supported": False,
            "reason": (
                "This dataset lacks suitable historical price/index data. "
                "A chronological date/time column and a price or index metric (e.g. CPI, Price, Unit_Price, Cost) are required."
            ),
            "mode": "none",
            "date_column": date_col,
            "price_column": primary_price_col,
            "available_price_columns": available_price_cols,
            "dimension_columns": [],
            "dimension_values": {},
            "categories": [],
            "products": [],
            "regions": [],
            "min_date": None,
            "max_date": None,
            "total_observations": 0,
        }

    # 3. Detect Categorical Dimensions (Category, Product, Region, Segment, etc.)
    dim_cols = []
    cat_named_cols = []
    prod_named_cols = []
    reg_named_cols = []

    for col_name in df.columns:
        if col_name in (date_col, primary_price_col):
            continue
        low = col_name.lower()
        is_text = df[col_name].dtype == "object" or any(
            c.name == col_name and c.inferred_type in ("categorical", "text") for c in columns
        )
        if is_text:
            if "category" in low or "cat" in low:
                cat_named_cols.append(col_name)
            elif "product" in low or "item" in low or "sku" in low:
                prod_named_cols.append(col_name)
            elif "region" in low or "area" in low or "country" in low or "state" in low:
                reg_named_cols.append(col_name)
            else:
                dim_cols.append(col_name)

    # Ordered dimension priority: Category, Product, Region, then others
    ordered_dimensions = cat_named_cols + prod_named_cols + reg_named_cols + dim_cols

    dim_values: Dict[str, List[str]] = {}
    for c in ordered_dimensions[:6]:
        unique_vals = [str(v) for v in df[c].dropna().unique().tolist() if str(v).strip()]
        dim_values[c] = unique_vals[:50]

    categories_list = dim_values.get(cat_named_cols[0], []) if cat_named_cols else []
    products_list = dim_values.get(prod_named_cols[0], []) if prod_named_cols else []
    regions_list = dim_values.get(reg_named_cols[0], []) if reg_named_cols else []

    valid_dates = pd.to_datetime(df[date_col], errors="coerce").dropna().sort_values()
    min_date = valid_dates.iloc[0].strftime("%Y-%m-%d") if not valid_dates.empty else None
    max_date = valid_dates.iloc[-1].strftime("%Y-%m-%d") if not valid_dates.empty else None

    mode_label = (
        "Consumer Price Index (CPI)"
        if default_mode == "cpi"
        else "Price Index Estimate (Base = 100)"
        if default_mode == "price_index"
        else "Product Price Forecast"
    )

    return {
        "supported": True,
        "mode": default_mode,
        "mode_label": mode_label,
        "date_column": date_col,
        "price_column": primary_price_col,
        "available_price_columns": available_price_cols,
        "dimension_columns": ordered_dimensions,
        "dimension_values": dim_values,
        "categories": categories_list,
        "products": products_list,
        "regions": regions_list,
        "min_date": min_date,
        "max_date": max_date,
        "total_observations": len(valid_dates),
    }


def run_cpi_forecast(
    engine: Engine,
    dataset: Dataset,
    columns: List[DatasetColumn],
    analysis_mode: Optional[str] = "auto",
    date_column: Optional[str] = None,
    price_column: Optional[str] = None,
    dimension_column: Optional[str] = None,
    dimension_value: Optional[str] = "All",
    horizon_months: int = 6,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes historical monthly aggregation, gap handling via interpolation,
    statistical time-series forecasting (Holt's Exponential Smoothing / Adaptive Trend),
    95% prediction intervals, and consumer market purchasing guidance.
    """
    caps = detect_cpi_capabilities(engine, dataset, columns)
    if not caps["supported"]:
        raise ValueError(caps.get("reason") or "CPI / Price forecasting is not supported for this dataset.")

    df = read_dataframe(engine, dataset.storage_table_name)
    resolved_date = date_column or caps["date_column"]
    resolved_price = price_column or caps["price_column"]

    if not resolved_date or resolved_date not in df.columns:
        raise ValueError(f"Date column '{resolved_date}' not found in dataset.")
    if not resolved_price or resolved_price not in df.columns:
        raise ValueError(f"Price/index column '{resolved_price}' not found in dataset.")

    # Determine analysis mode
    if analysis_mode in ("cpi", "product_price", "price_index"):
        mode = analysis_mode
    else:
        low_price = resolved_price.lower()
        if "cpi" in low_price or "consumer_price_index" in low_price:
            mode = "cpi"
        elif "price_index" in low_price:
            mode = "price_index"
        elif any(k in low_price for k in ["unit_price", "price", "rate"]):
            mode = "product_price"
        else:
            mode = caps["mode"] if caps["mode"] != "none" else "product_price"

    if mode == "cpi":
        mode_label = "Consumer Price Index (CPI)"
        unit_label = "Index Points"
    elif mode == "price_index":
        mode_label = "Price Index Estimate (Base Period = 100)"
        unit_label = "Index Points (Base = 100)"
    else:
        mode = "product_price"
        mode_label = "Product Price Forecast"
        unit_label = "Nominal Price ($)"

    # Identify active dimension column
    active_dim_col = dimension_column
    if not active_dim_col and caps["dimension_columns"]:
        active_dim_col = caps["dimension_columns"][0]

    # Filter by dimension value if specified
    if active_dim_col and active_dim_col in df.columns and dimension_value and dimension_value != "All":
        df = df[df[active_dim_col].astype(str) == str(dimension_value)].copy()

    # Parse and clean dates
    df[resolved_date] = pd.to_datetime(df[resolved_date], errors="coerce")
    df = df.dropna(subset=[resolved_date])

    # Parse and clean numeric price/index values
    df[resolved_price] = pd.to_numeric(
        df[resolved_price].astype(str).str.replace(",", "").str.strip(),
        errors="coerce",
    )
    df = df.dropna(subset=[resolved_price])

    # Date range filters
    if start_date:
        df = df[df[resolved_date] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df[resolved_date] <= pd.to_datetime(end_date)]

    if len(df) < 3:
        raise ValueError(
            "Insufficient historical observations for the selected filters. "
            "At least 3 valid chronological observations are required."
        )

    # Monthly aggregation: calculate mean for each month
    df["Month_Period"] = df[resolved_date].dt.to_period("M").dt.to_timestamp()
    monthly_series = df.groupby("Month_Period")[resolved_price].mean().sort_index()

    # Handle temporal gaps without treating missing values as zero
    full_date_range = pd.date_range(
        start=monthly_series.index.min(),
        end=monthly_series.index.max(),
        freq="MS",
    )
    if len(full_date_range) > len(monthly_series):
        monthly_series = monthly_series.reindex(full_date_range).interpolate(method="linear").bfill().ffill()

    if len(monthly_series) < 3:
        raise ValueError(
            "Insufficient historical monthly intervals for reliable forecasting. "
            "At least 3 monthly periods are required."
        )

    # Price Index normalization if in price_index mode
    if mode == "price_index":
        base_val = float(monthly_series.iloc[0])
        if np.isclose(base_val, 0.0):
            base_val = 1.0
        series = (monthly_series / base_val) * 100.0
    else:
        series = monthly_series

    n = len(series)
    dates_list = series.index.tolist()
    y = series.values.astype(float)

    # Check for constant or zero-variance series
    is_constant = bool(np.isclose(np.std(y), 0.0) or np.isclose(np.min(y), np.max(y)))

    horizon = max(1, min(int(horizon_months), 24))

    fitted_values: np.ndarray
    forecast_values: np.ndarray
    sigma_eps: float
    model_name: str
    alpha: float = 0.2

    if is_constant:
        model_name = "Constant Series Persistence"
        const_val = float(y[-1])
        fitted_values = np.full(n, const_val, dtype=float)
        forecast_values = np.full(horizon, const_val, dtype=float)
        sigma_eps = 0.0
        lower_ci = forecast_values.copy()
        upper_ci = forecast_values.copy()
    else:
        use_holt = False
        if n >= 6:
            try:
                from statsmodels.tsa.api import Holt
                damped = bool(n >= 12)
                holt_model = Holt(series, initialization_method="estimated", damped_trend=damped)
                fit_res = holt_model.fit(optimized=True)
                forecast_values = np.asarray(fit_res.forecast(horizon).values, dtype=float)
                fitted_values = np.asarray(fit_res.fittedvalues.values, dtype=float)
                model_name = (
                    "Holt's Exponential Smoothing (Damped Trend)"
                    if damped
                    else "Holt's Exponential Smoothing (Linear Trend)"
                )
                residuals = y - fitted_values
                sigma_eps = float(np.std(residuals, ddof=2)) if len(residuals) > 2 else float(np.std(residuals))
                alpha = float(fit_res.params.get("smoothing_level", 0.3) or 0.3)
                use_holt = True
            except Exception as e:
                logger.warning("Holt exponential smoothing fallback: %s", e)

        if not use_holt:
            x_arr = np.arange(n, dtype=float)
            slope, intercept = np.polyfit(x_arr, y, 1)
            fitted_values = slope * x_arr + intercept
            future_x = np.arange(n, n + horizon, dtype=float)
            forecast_values = slope * future_x + intercept
            model_name = "Linear Trend Regression"
            residuals = y - fitted_values
            sigma_eps = float(np.std(residuals, ddof=2)) if len(residuals) > 2 else float(np.std(residuals))
            alpha = 0.2

        # 95% Out-of-sample prediction intervals
        h_steps = np.arange(1, horizon + 1, dtype=float)
        eff_alpha = max(0.2, alpha)
        se_h = sigma_eps * np.sqrt(1.0 + (h_steps - 1.0) * (eff_alpha ** 2))
        margin = 1.96 * se_h
        upper_ci = forecast_values + margin
        lower_ci = np.maximum(0.0, forecast_values - margin)

    residuals_all = y - fitted_values
    fit_rmse = round(float(np.sqrt(np.mean(residuals_all ** 2))), 3)
    nonzero_mask = ~np.isclose(y, 0.0)
    if np.any(nonzero_mask):
        fit_mape = round(float(np.mean(np.abs(residuals_all[nonzero_mask] / y[nonzero_mask]))) * 100.0, 2)
    else:
        fit_mape = 0.0

    points = []
    for i in range(n - 1):
        points.append({
            "date": dates_list[i].strftime("%Y-%m-%d"),
            "actual": round(float(y[i]), 2),
            "predicted": None,
            "lower_bound": None,
            "upper_bound": None,
            "is_forecast": False,
        })

    last_date = dates_list[-1]
    last_actual = round(float(y[-1]), 2)
    points.append({
        "date": last_date.strftime("%Y-%m-%d"),
        "actual": last_actual,
        "predicted": last_actual,
        "lower_bound": last_actual,
        "upper_bound": last_actual,
        "is_forecast": False,
        "is_anchor": True,
    })

    forecast_start_date = (last_date + pd.DateOffset(months=1)).strftime("%Y-%m-%d")
    forecast_end_date = (last_date + pd.DateOffset(months=horizon)).strftime("%Y-%m-%d")

    for step in range(1, horizon + 1):
        future_date = (last_date + pd.DateOffset(months=step)).strftime("%Y-%m-%d")
        points.append({
            "date": future_date,
            "actual": None,
            "predicted": round(float(forecast_values[step - 1]), 2),
            "lower_bound": round(float(lower_ci[step - 1]), 2),
            "upper_bound": round(float(upper_ci[step - 1]), 2),
            "is_forecast": True,
        })

    current_index = last_actual
    forecasted_index = round(float(forecast_values[-1]), 2)

    if current_index > 0:
        expected_change_pct = round(((forecasted_index - current_index) / current_index) * 100.0, 2)
    else:
        expected_change_pct = 0.0

    if current_index > 0 and forecasted_index > 0:
        ratio = forecasted_index / current_index
        annualized_rate = round(((ratio ** (12.0 / horizon)) - 1.0) * 100.0, 2)
    else:
        annualized_rate = round(expected_change_pct * (12.0 / horizon), 2)

    mean_val = float(np.mean(y))
    volatility_pct = round((np.std(y) / (abs(mean_val) or 1.0)) * 100.0, 2)

    highest_growth_dim = "N/A"
    lowest_growth_dim = "N/A"
    if active_dim_col and active_dim_col in df.columns:
        dim_growth = {}
        for dim_name, group in df.groupby(active_dim_col):
            group_monthly = group.groupby("Month_Period")[resolved_price].mean().sort_index()
            if len(group_monthly) >= 2:
                g_start = float(group_monthly.iloc[0])
                g_end = float(group_monthly.iloc[-1])
                if g_start > 0:
                    pct = ((g_end - g_start) / g_start) * 100.0
                    dim_growth[str(dim_name)] = pct

        if dim_growth:
            sorted_dims = sorted(dim_growth.items(), key=lambda item: item[1], reverse=True)
            highest_growth_dim = f"{sorted_dims[0][0]} (+{sorted_dims[0][1]:.1f}%)"
            lowest_growth_dim = f"{sorted_dims[-1][0]} ({sorted_dims[-1][1]:+.1f}%)"

    if is_constant:
        buying_recommendation = (
            f"Completely Stable Pricing: Price series has remained constant at {current_index} {unit_label}. "
            "No projected escalation detected; standard operational procurement schedules are recommended."
        )
    elif expected_change_pct >= 3.0:
        buying_recommendation = (
            f"Favorable Immediate Buying Window: Prices are projected to increase by {expected_change_pct}% "
            f"over the next {horizon} months (compounded annualized rate of {annualized_rate}%). "
            f"Securing inventory or contracting supplier terms early may hedge against anticipated price escalation."
        )
    elif expected_change_pct <= -2.0:
        buying_recommendation = (
            f"Favorable Delayed Buying Window: Prices are projected to decline by {abs(expected_change_pct)}% "
            f"over the next {horizon} months. Deferring non-urgent or discretionary purchases can yield significant cost savings."
        )
    else:
        buying_recommendation = (
            f"Neutral Pricing Environment: Projected price movement is modest ({expected_change_pct}% over {horizon} months). "
            "Maintain standard procurement cycles aligned with operational inventory demand."
        )

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "mode": mode,
        "mode_label": mode_label,
        "unit_label": unit_label,
        "date_column": resolved_date,
        "price_column": resolved_price,
        "dimension_column": active_dim_col,
        "selected_dimension_value": dimension_value or "All",
        "horizon_months": horizon,
        "forecast_start_date": forecast_start_date,
        "forecast_end_date": forecast_end_date,
        "current_index": current_index,
        "forecasted_index": forecasted_index,
        "expected_change_pct": expected_change_pct,
        "annualized_rate_pct": annualized_rate,
        "volatility_pct": volatility_pct,
        "historical_observations": n,
        "model_name": model_name,
        "fit_rmse": fit_rmse,
        "fit_mape": fit_mape,
        "is_constant_series": is_constant,
        "highest_growth_category": highest_growth_dim,
        "lowest_growth_category": lowest_growth_dim,
        "purchasing_recommendation": buying_recommendation,
        "confidence_interval_note": (
            "95% prediction intervals model statistical error variance expanding with horizon distance (t)."
            if not is_constant
            else "Series is constant; error variance and interval margins are zero."
        ),
        "disclaimer": (
            "Statistical projections are generated using historical time-series smoothing models. "
            "They represent analytical estimates and do not constitute purchasing guarantees or financial advice."
        ),
        "points": points,
    }


def get_historical_series(
    engine: Engine,
    dataset: Dataset,
    columns: List[DatasetColumn],
    date_column: Optional[str] = None,
    price_column: Optional[str] = None,
    dimension_column: Optional[str] = None,
    dimension_value: Optional[str] = "All",
) -> Dict[str, Any]:
    """
    Extracts chronological monthly aggregated historical values for the dataset.
    """
    caps = detect_cpi_capabilities(engine, dataset, columns)
    if not caps["supported"]:
        raise ValueError(caps.get("reason") or "CPI forecasting is not supported for this dataset.")

    df = read_dataframe(engine, dataset.storage_table_name)
    resolved_date = date_column or caps["date_column"]
    resolved_price = price_column or caps["price_column"]

    if not resolved_date or resolved_date not in df.columns:
        raise ValueError(f"Date column '{resolved_date}' not found in dataset.")
    if not resolved_price or resolved_price not in df.columns:
        raise ValueError(f"Price/index column '{resolved_price}' not found in dataset.")

    active_dim_col = dimension_column or (caps["dimension_columns"][0] if caps["dimension_columns"] else None)
    if active_dim_col and active_dim_col in df.columns and dimension_value and dimension_value != "All":
        df = df[df[active_dim_col].astype(str) == str(dimension_value)].copy()

    df[resolved_date] = pd.to_datetime(df[resolved_date], errors="coerce")
    df = df.dropna(subset=[resolved_date])
    df[resolved_price] = pd.to_numeric(df[resolved_price], errors="coerce")
    df = df.dropna(subset=[resolved_price])

    if len(df) < 2:
        raise ValueError("Insufficient historical observations for the selected series.")

    df["Month_Period"] = df[resolved_date].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("Month_Period")[resolved_price].mean().sort_index()

    full_date_range = pd.date_range(start=monthly.index.min(), end=monthly.index.max(), freq="MS")
    if len(full_date_range) > len(monthly):
        monthly = monthly.reindex(full_date_range).interpolate(method="linear").bfill().ffill()

    series_data = [
        {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 2)}
        for d, v in zip(monthly.index, monthly.values)
    ]

    return {
        "dataset_id": dataset.id,
        "date_column": resolved_date,
        "price_column": resolved_price,
        "dimension_column": active_dim_col,
        "dimension_value": dimension_value or "All",
        "total_observations": len(series_data),
        "series": series_data,
    }

