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


def apply_selected_quality_actions(
    df: pd.DataFrame,
    selected_issue_ids: list[str],
    all_issues: list[Any],
) -> tuple[pd.DataFrame, dict]:
    """
    Applies only user-selected deterministic transformations based on detected QualityIssues.
    Never executes arbitrary AI code or modifies raw original tables.
    """
    import numpy as np

    df = df.copy()
    rows_before = len(df)
    actions_applied: list[str] = []
    changes_detail: dict[str, Any] = {}

    selected_set = set(selected_issue_ids)
    selected_issues = [iss for iss in all_issues if getattr(iss, "id", None) in selected_set or (isinstance(iss, dict) and iss.get("id") in selected_set)]

    # 1. First Pass: Deduplication if selected
    dup_issues = [i for i in selected_issues if (getattr(i, "action_type", None) or (isinstance(i, dict) and i.get("action_type"))) == "drop_duplicates"]
    if dup_issues:
        before = len(df)
        df = df.drop_duplicates()
        dropped = before - len(df)
        actions_applied.append(f"Dropped {dropped} duplicate rows")
        changes_detail["duplicates_dropped"] = dropped

    # 2. Column-level operations
    for iss in selected_issues:
        action_type = getattr(iss, "action_type", None) or (iss.get("action_type") if isinstance(iss, dict) else None)
        col = getattr(iss, "column", None) or (iss.get("column") if isinstance(iss, dict) else None)

        if not action_type or action_type == "drop_duplicates" or not col or col not in df.columns:
            continue

        s = df[col]

        # Whitespace trimming
        if action_type == "trim_whitespace":
            df[col] = s.astype(str).str.strip().replace({"nan": pd.NA, "": pd.NA, "None": pd.NA, "null": pd.NA, "NULL": pd.NA})
            actions_applied.append(f"Trimmed whitespace in column '{col}'")
            changes_detail[f"{col}_trimmed"] = True

        # Text casing standardization
        elif action_type == "standardize_text_casing":
            clean_s = s.astype(str).str.strip()
            df[col] = clean_s.apply(lambda x: x.title() if x and x.lower() not in ("nan", "none", "null") else x)
            actions_applied.append(f"Standardized text casing to Title Case in '{col}'")
            changes_detail[f"{col}_casing"] = "title"

        # Numeric formatting cleaning (e.g. "$1,25,000")
        elif action_type == "clean_numeric_formatting":
            clean_num = s.astype(str).str.replace(",", "").str.replace("$", "").str.replace("%", "").str.strip()
            df[col] = pd.to_numeric(clean_num, errors="coerce")
            actions_applied.append(f"Cleaned non-numeric characters and formatted '{col}' as float")
            changes_detail[f"{col}_numeric_cleaned"] = True

        # Missing values: Numeric Median
        elif action_type == "fill_numeric_median":
            num_s = pd.to_numeric(s.astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
            med = float(num_s.median()) if not num_s.dropna().empty else 0.0
            if np.isnan(med):
                med = 0.0
            null_count = int(num_s.isna().sum())
            df[col] = num_s.fillna(med)
            actions_applied.append(f"Imputed {null_count} missing values in '{col}' with median ({med:.2f})")
            changes_detail[f"{col}_imputed_median"] = {"count": null_count, "fill_value": med}

        # Missing values: Categorical Mode
        elif action_type == "fill_categorical_mode":
            non_null = s.replace({"nan": pd.NA, "": pd.NA, "None": pd.NA, "null": pd.NA, "NULL": pd.NA}).dropna()
            mode_series = non_null.mode()
            fill_val = str(mode_series.iloc[0]) if not mode_series.empty else "Unknown"
            null_count = int(s.isna().sum()) + int(s.isin(["nan", "", "None", "null"]).sum())
            df[col] = s.replace({"nan": pd.NA, "": pd.NA, "None": pd.NA, "null": pd.NA, "NULL": pd.NA}).fillna(fill_val)
            actions_applied.append(f"Imputed {null_count} missing values in '{col}' with mode ('{fill_val}')")
            changes_detail[f"{col}_imputed_mode"] = {"count": null_count, "fill_value": fill_val}

        # Clamp invalid negative values
        elif action_type == "clamp_negative_values":
            num_s = pd.to_numeric(s.astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
            neg_count = int((num_s < 0).sum())
            df[col] = np.maximum(num_s, 0.0)
            actions_applied.append(f"Clamped {neg_count} negative values in '{col}' to 0.0")
            changes_detail[f"{col}_clamped_negatives"] = neg_count

        # Cap statistical outliers
        elif action_type == "cap_outliers_iqr":
            num_s = pd.to_numeric(s.astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
            valid = num_s.dropna()
            if len(valid) > 4:
                q25 = valid.quantile(0.25)
                q75 = valid.quantile(0.75)
                iqr = q75 - q25
                lower_b = q25 - 2.5 * iqr
                upper_b = q75 + 2.5 * iqr
                capped_count = int(((num_s < lower_b) | (num_s > upper_b)).sum())
                df[col] = num_s.clip(lower=lower_b, upper=upper_b)
                actions_applied.append(f"Capped {capped_count} extreme outlier values in '{col}' at 2.5x IQR boundaries")
                changes_detail[f"{col}_capped_outliers"] = capped_count

        # Standardize dates
        elif action_type == "standardize_dates":
            parsed = pd.to_datetime(s.astype(str).str.strip(), errors="coerce")
            formatted = parsed.dt.strftime("%Y-%m-%d")
            # Fill unparseable with original string
            df[col] = formatted.fillna(s)
            actions_applied.append(f"Standardized date formatting in '{col}' to YYYY-MM-DD")
            changes_detail[f"{col}_dates_standardized"] = True

    report = {
        "rows_before": rows_before,
        "rows_after": len(df),
        "actions_applied": actions_applied,
        "changes_detail": changes_detail,
    }
    return df, report
