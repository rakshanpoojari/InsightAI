"""Real, deterministic data cleaning transforms — nothing here is faked or hardcoded per-dataset."""
from __future__ import annotations

import pandas as pd

from app.schemas import CleaningOptions
from app.services.data_profiling import _infer_column_type


def clean_dataframe(df: pd.DataFrame, options: CleaningOptions) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    report = {
        "rows_before": len(df),
        "duplicates_dropped": 0,
        "whitespace_trimmed_columns": [],
        "missing_filled": {},
    }

    if options.trim_whitespace:
        obj_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
        for col in obj_cols:
            df[col] = df[col].astype(str).str.strip().replace({"nan": pd.NA, "": pd.NA})
        report["whitespace_trimmed_columns"] = obj_cols

    if options.drop_duplicate_rows:
        before = len(df)
        df = df.drop_duplicates()
        report["duplicates_dropped"] = before - len(df)

    for col in df.columns:
        col_type = _infer_column_type(df[col])
        n_missing = int(df[col].isna().sum())
        if n_missing == 0:
            continue

        if col_type == "numeric" and options.fill_missing_numeric != "none":
            if options.fill_missing_numeric == "median":
                fill_value = df[col].median()
            elif options.fill_missing_numeric == "mean":
                fill_value = df[col].mean()
            else:
                fill_value = 0
            df[col] = df[col].fillna(fill_value)
            report["missing_filled"][col] = {"strategy": options.fill_missing_numeric, "count": n_missing}

        elif col_type == "categorical" and options.fill_missing_categorical != "none":
            if options.fill_missing_categorical == "mode":
                mode_vals = df[col].mode()
                fill_value = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
            else:
                fill_value = "Unknown"
            df[col] = df[col].fillna(fill_value)
            report["missing_filled"][col] = {"strategy": options.fill_missing_categorical, "count": n_missing}

    report["rows_after"] = len(df)
    return df, report
