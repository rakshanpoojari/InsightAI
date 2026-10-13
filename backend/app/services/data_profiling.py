"""
Real data profiling logic — no mocked results.

Given a pandas DataFrame, this module:
- Infers a semantic type per column (numeric / categorical / datetime / boolean / text)
- Computes missing value counts, unique counts, and per-type statistics
- Computes an overall data quality score (0-100) from completeness, duplication,
  and type-consistency signals
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _infer_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "text"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Try parsing as datetime (only if it looks date-like to avoid false positives
    # on things like free-text or ID columns)
    sample = non_null.astype(str).head(50)
    date_like = sample.str.match(
        r"^\d{4}-\d{2}-\d{2}|^\d{1,2}/\d{1,2}/\d{2,4}|^\d{1,2}-\d{1,2}-\d{2,4}"
    )
    if date_like.mean() > 0.7:
        try:
            parsed = pd.to_datetime(non_null, errors="coerce")
            if parsed.notna().mean() > 0.85:
                return "datetime"
        except Exception:
            pass

    # Categorical vs free text: low cardinality relative to row count => categorical
    n_unique = non_null.nunique()
    n_total = len(non_null)
    if n_unique <= max(50, int(n_total * 0.05)):
        return "categorical"

    return "text"


def _column_stats(series: pd.Series, col_type: str) -> dict:
    non_null = series.dropna()
    if col_type == "numeric":
        if non_null.empty:
            return {}
        return {
            "min": float(non_null.min()),
            "max": float(non_null.max()),
            "mean": float(non_null.mean()),
            "median": float(non_null.median()),
            "std": float(non_null.std()) if len(non_null) > 1 else 0.0,
        }
    if col_type == "categorical":
        top = non_null.astype(str).value_counts().head(5)
        return {"top_values": {str(k): int(v) for k, v in top.items()}}
    if col_type == "datetime":
        try:
            parsed = pd.to_datetime(non_null, errors="coerce").dropna()
            if parsed.empty:
                return {}
            return {"min_date": str(parsed.min()), "max_date": str(parsed.max())}
        except Exception:
            return {}
    return {}


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    """Return a list of per-column profile dicts."""
    profiles = []
    n_rows = len(df)
    for col in df.columns:
        series = df[col]
        col_type = _infer_column_type(series)
        missing_count = int(series.isna().sum())
        missing_pct = round((missing_count / n_rows) * 100, 2) if n_rows else 0.0
        unique_count = int(series.nunique(dropna=True))
        sample_values = series.dropna().astype(str).unique()[:5].tolist()

        profiles.append(
            {
                "name": str(col),
                "inferred_type": col_type,
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "unique_count": unique_count,
                "sample_values": sample_values,
                "stats": _column_stats(series, col_type),
            }
        )
    return profiles


def compute_quality_score(df: pd.DataFrame, profiles: list[dict]) -> float:
    """
    Composite data quality score (0-100), built from three real, measurable signals:
      - Completeness: 1 - (overall missing cell ratio)
      - Uniqueness: 1 - (duplicate row ratio)
      - Consistency: fraction of columns that are NOT ambiguous free-text
        (i.e. we could confidently infer a semantic type)
    Weighted average: completeness 50%, uniqueness 30%, consistency 20%.
    """
    if df.empty:
        return 0.0

    total_cells = df.shape[0] * df.shape[1]
    missing_cells = sum(p["missing_count"] for p in profiles)
    completeness = 1 - (missing_cells / total_cells) if total_cells else 0

    dup_rows = int(df.duplicated().sum())
    uniqueness = 1 - (dup_rows / len(df)) if len(df) else 0

    confident_types = sum(1 for p in profiles if p["inferred_type"] != "text")
    consistency = confident_types / len(profiles) if profiles else 0

    score = (completeness * 0.5 + uniqueness * 0.3 + consistency * 0.2) * 100
    return round(max(0.0, min(100.0, score)), 1)


def detect_duplicate_rows(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())
