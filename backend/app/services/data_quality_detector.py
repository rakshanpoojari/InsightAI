from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.schemas import QualityIssue, QualityReportResponse
from app.services.data_profiling import _infer_column_type


def detect_data_quality_issues(df: pd.DataFrame, dataset_id: int, dataset_name: str) -> Tuple[List[QualityIssue], float, Dict[str, int], Dict[str, int]]:
    """
    Performs comprehensive deterministic data quality detection across 9 key categories:
    1. Missing values and nulls
    2. Duplicate rows and records
    3. Inconsistent text capitalization & whitespace
    4. Incorrect or inconsistent date formats
    5. Numeric columns containing string/localized formatting
    6. Potential outliers
    7. Invalid negative values or impossible values
    8. Inconsistent data types
    9. Potentially inconsistent calculated columns
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    total_cols = df.shape[1]

    if df.empty or total_rows == 0:
        return [], 0.0, {}, {}

    # Category counters
    cat_counts: Dict[str, int] = {
        "missing_values": 0,
        "duplicates": 0,
        "text_inconsistency": 0,
        "invalid_dates": 0,
        "numeric_formatting": 0,
        "outliers": 0,
        "invalid_values": 0,
        "type_inconsistency": 0,
        "calculation_anomaly": 0,
    }
    sev_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}

    # 1. Duplicate Rows Detection
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        pct = round((dup_count / total_rows) * 100, 2)
        sev = "high" if pct > 5 else "medium"
        issues.append(
            QualityIssue(
                id="issue-duplicates-all",
                category="duplicates",
                severity=sev,
                column=None,
                affected_rows_count=dup_count,
                affected_percentage=pct,
                sample_values=[f"Row {idx}" for idx in df[df.duplicated()].index[:3].tolist()],
                title=f"Detected {dup_count} Duplicate Row(s)",
                description=f"{dup_count} exact duplicate record(s) found across all dataset dimensions ({pct}% of total records).",
                why_it_matters="Duplicate rows distort aggregate calculations (SUM, COUNT, AVG) and skew BI KPI dashboards with double-counted metrics.",
                recommended_action="Remove redundant duplicate rows, retaining the primary first occurrence.",
                action_type="drop_duplicates",
                expected_impact=f"Improves uniqueness score and eliminates {dup_count} redundant record(s).",
                risks_assumptions="Assumes rows with identical values across every dimension represent accidental duplicates.",
                is_selected_by_default=True,
            )
        )
        cat_counts["duplicates"] += 1
        sev_counts[sev] += 1

    # Inspect columns
    for col in df.columns:
        s = df[col]
        col_type = _infer_column_type(s)

        # 2. Missing Values and Nulls
        # Detect true nulls + string placeholder tokens
        null_mask = s.isna()
        if s.dtype == "object" or pd.api.types.is_string_dtype(s):
            str_vals = s.astype(str).str.strip().str.lower()
            token_mask = str_vals.isin(["nan", "null", "none", "n/a", "na", "", "undefined", "?"])
            combined_null = null_mask | token_mask
        else:
            combined_null = null_mask

        n_missing = int(combined_null.sum())
        if n_missing > 0:
            pct = round((n_missing / total_rows) * 100, 2)
            sev = "high" if pct > 20 else ("medium" if pct > 5 else "low")
            
            if col_type == "numeric":
                action_type = "fill_numeric_median"
                action_name = "Impute missing values using median (robust to outliers)"
            elif col_type in ("categorical", "text"):
                action_type = "fill_categorical_mode"
                action_name = "Impute missing values using most frequent mode value"
            else:
                action_type = "fill_categorical_mode"
                action_name = "Impute missing values with appropriate placeholder"

            issues.append(
                QualityIssue(
                    id=f"issue-missing-{col}",
                    category="missing_values",
                    severity=sev,
                    column=str(col),
                    affected_rows_count=n_missing,
                    affected_percentage=pct,
                    sample_values=[f"Null in row {idx}" for idx in df[combined_null].index[:3].tolist()],
                    title=f"Missing Values in '{col}' ({pct}%)",
                    description=f"Column '{col}' has {n_missing} missing or unpopulated cell(s) ({pct}% of records).",
                    why_it_matters="Missing values cause query exclusions in SQL joins/aggregations and introduce bias in predictive analytics.",
                    recommended_action=action_name,
                    action_type=action_type,
                    expected_impact=f"Restores 100% completeness for column '{col}' across all {total_rows} rows.",
                    risks_assumptions=f"Assumes missing values can be reasonably approximated using statistical central tendency.",
                    is_selected_by_default=True,
                )
            )
            cat_counts["missing_values"] += 1
            sev_counts[sev] += 1

        # 3. Text Inconsistency: Whitespace & Mixed Casing
        if col_type in ("categorical", "text") and not s.dropna().empty:
            non_null_s = s.dropna().astype(str)
            
            # Check leading/trailing whitespace
            has_ws = (non_null_s.str.strip() != non_null_s)
            ws_count = int(has_ws.sum())
            if ws_count > 0:
                pct = round((ws_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        id=f"issue-whitespace-{col}",
                        category="text_inconsistency",
                        severity="medium",
                        column=str(col),
                        affected_rows_count=ws_count,
                        affected_percentage=pct,
                        sample_values=[repr(v) for v in non_null_s[has_ws].head(3).tolist()],
                        title=f"Leading/Trailing Whitespace in '{col}'",
                        description=f"{ws_count} text value(s) in '{col}' contain hidden leading or trailing spaces.",
                        why_it_matters="Hidden whitespace causes identical categories to fragment into separate buckets during GROUP BY queries.",
                        recommended_action="Trim all leading and trailing whitespace characters.",
                        action_type="trim_whitespace",
                        expected_impact=f"Standardizes category labels in '{col}' and prevents duplicate GROUP BY groupings.",
                        risks_assumptions="Safe string trim transform with zero data loss.",
                        is_selected_by_default=True,
                    )
                )
                cat_counts["text_inconsistency"] += 1
                sev_counts["medium"] += 1

            # Check inconsistent casing (e.g. "Tech", "tech", "TECH")
            lowered = non_null_s.str.strip().str.lower()
            raw_unique = non_null_s.str.strip().nunique()
            low_unique = lowered.nunique()
            if raw_unique > low_unique and raw_unique <= 100:
                diff_count = raw_unique - low_unique
                issues.append(
                    QualityIssue(
                        id=f"issue-casing-{col}",
                        category="text_inconsistency",
                        severity="medium",
                        column=str(col),
                        affected_rows_count=diff_count,
                        affected_percentage=round((diff_count / total_rows) * 100, 2),
                        sample_values=non_null_s.head(4).tolist(),
                        title=f"Inconsistent Text Capitalization in '{col}'",
                        description=f"Found {diff_count} casing variant(s) of identical categories (e.g. lowercase vs capitalized).",
                        why_it_matters="Case-sensitive database engines treat 'Electronics' and 'electronics' as two separate categories.",
                        recommended_action="Standardize all text labels in this column to proper Title Case.",
                        action_type="standardize_text_casing",
                        expected_impact=f"Unifies fragmented labels into {low_unique} clean categorical values.",
                        risks_assumptions="Assumes capitalization differences represent data-entry variation rather than distinct entities.",
                        is_selected_by_default=True,
                    )
                )
                cat_counts["text_inconsistency"] += 1
                sev_counts["medium"] += 1

        # 4. Numeric Formatting & String Numbers (e.g. "$1,25,000", "50%")
        if s.dtype == "object":
            non_null_s = s.dropna().astype(str).str.strip()
            # Test if removing commas and currency symbols allows numeric conversion
            cleaned_attempt = non_null_s.str.replace(",", "").str.replace("$", "").str.replace("%", "").str.strip()
            numeric_valid = pd.to_numeric(cleaned_attempt, errors="coerce")
            
            # If >60% can be converted to numeric but column is currently object
            if numeric_valid.notna().mean() >= 0.6 and numeric_valid.notna().sum() > 0:
                unformatted_mask = (non_null_s.str.contains(r"[,\$%]", regex=True))
                fmt_count = int(unformatted_mask.sum())
                if fmt_count > 0:
                    pct = round((fmt_count / total_rows) * 100, 2)
                    issues.append(
                        QualityIssue(
                            id=f"issue-numeric-fmt-{col}",
                            category="numeric_formatting",
                            severity="high",
                            column=str(col),
                            affected_rows_count=fmt_count,
                            affected_percentage=pct,
                            sample_values=non_null_s[unformatted_mask].head(3).tolist(),
                            title=f"Numeric Column Formatted as Text in '{col}'",
                            description=f"{fmt_count} numerical values in '{col}' contain comma separators, currency symbols, or percent signs.",
                            why_it_matters="Stored as text, this column cannot be aggregated with SUM/AVG, graphed in charts, or used in forecasting.",
                            recommended_action="Strip non-numeric characters (commas, currency signs) and cast to standard numeric float.",
                            action_type="clean_numeric_formatting",
                            expected_impact=f"Enables full mathematical aggregation, charting, and statistical modeling on '{col}'.",
                            risks_assumptions="Assumes symbols like commas and dollar signs represent display formatting.",
                            is_selected_by_default=True,
                        )
                    )
                    cat_counts["numeric_formatting"] += 1
                    sev_counts["high"] += 1

        # 5. Invalid Negative Values
        num_series = pd.to_numeric(s.astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
        col_lower = str(col).lower()
        is_suspicious_negative_col = any(k in col_lower for k in ["sales", "revenue", "price", "unit_price", "units", "quantity", "qty", "volume", "cost", "cpi"])
        
        if is_suspicious_negative_col and num_series.notna().sum() > 0:
            negative_mask = num_series < 0
            neg_count = int(negative_mask.sum())
            if neg_count > 0:
                pct = round((neg_count / total_rows) * 100, 2)
                issues.append(
                    QualityIssue(
                        id=f"issue-negative-{col}",
                        category="invalid_values",
                        severity="high",
                        column=str(col),
                        affected_rows_count=neg_count,
                        affected_percentage=pct,
                        sample_values=[f"{v:.2f}" for v in num_series[negative_mask].head(3).tolist()],
                        title=f"Suspicious Negative Values in '{col}'",
                        description=f"{neg_count} record(s) contain negative values in business metric '{col}' ({pct}% of records).",
                        why_it_matters="Negative quantities, sales, or prices typically represent logging reversals or data entry errors that distort business totals.",
                        recommended_action="Clamp negative values to 0 (or convert to positive magnitude if caused by sign error).",
                        action_type="clamp_negative_values",
                        expected_impact=f"Removes negative anomalies and prevents negative skew in revenue and volume totals.",
                        risks_assumptions="Assumes returns or corrections should be treated as non-negative transactions for baseline reporting.",
                        is_selected_by_default=False,  # Require explicit user opt-in
                    )
                )
                cat_counts["invalid_values"] += 1
                sev_counts["high"] += 1

        # 6. Potential Outliers (IQR + Z-Score)
        if col_type == "numeric" and num_series.notna().sum() > 8:
            valid_nums = num_series.dropna()
            q25 = valid_nums.quantile(0.25)
            q75 = valid_nums.quantile(0.75)
            iqr = q75 - q25
            if iqr > 0:
                lower_iqr = q25 - 2.5 * iqr
                upper_iqr = q75 + 2.5 * iqr
                outlier_mask = (valid_nums < lower_iqr) | (valid_nums > upper_iqr)
                outlier_count = int(outlier_mask.sum())
                if outlier_count > 0:
                    pct = round((outlier_count / total_rows) * 100, 2)
                    issues.append(
                        QualityIssue(
                            id=f"issue-outlier-{col}",
                            category="outliers",
                            severity="low" if pct < 3 else "medium",
                            column=str(col),
                            affected_rows_count=outlier_count,
                            affected_percentage=pct,
                            sample_values=[f"{v:,.2f}" for v in valid_nums[outlier_mask].head(3).tolist()],
                            title=f"Potential Statistical Outliers in '{col}'",
                            description=f"{outlier_count} observation(s) deviate beyond 2.5x IQR boundaries ({pct}% of total records).",
                            why_it_matters="Extreme statistical deviations can heavily influence mean averages and regression trend lines.",
                            recommended_action="Review flagged values. Optionally cap extreme outliers at upper/lower IQR bounds.",
                            action_type="cap_outliers_iqr",
                            expected_impact=f"Moderates extreme tail volatility in '{col}' without discarding records.",
                            risks_assumptions="Outliers may represent genuine high-value transactions; capping should only be applied if verified.",
                            is_selected_by_default=False,  # Require explicit user opt-in
                        )
                    )
                    cat_counts["outliers"] += 1
                    sev_counts["low" if pct < 3 else "medium"] += 1

        # 7. Date Format Inconsistencies
        if col_type == "datetime" or any(k in str(col).lower() for k in ["date", "period", "timestamp", "month", "time"]):
            if s.dtype == "object":
                non_null_dates = s.dropna().astype(str).str.strip()
                parsed_dates = pd.to_datetime(non_null_dates, errors="coerce")
                invalid_dates_count = int(parsed_dates.isna().sum())
                
                # Check for format variety (e.g. slashes vs dashes)
                has_slashes = non_null_dates.str.contains("/", regex=False).sum()
                has_dashes = non_null_dates.str.contains("-", regex=False).sum()
                mixed_format = (has_slashes > 0 and has_dashes > 0)

                if invalid_dates_count > 0 or mixed_format:
                    affected = invalid_dates_count if invalid_dates_count > 0 else int(has_slashes)
                    pct = round((affected / total_rows) * 100, 2)
                    issues.append(
                        QualityIssue(
                            id=f"issue-date-fmt-{col}",
                            category="invalid_dates",
                            severity="high" if invalid_dates_count > 0 else "medium",
                            column=str(col),
                            affected_rows_count=affected,
                            affected_percentage=pct,
                            sample_values=non_null_dates.head(3).tolist(),
                            title=f"Inconsistent Date Format in '{col}'",
                            description=f"Column '{col}' has {affected} date value(s) with inconsistent formats or unparseable timestamps.",
                            why_it_matters="Mixed date formats impede chronological sorting, time-series forecasting, and monthly rollups.",
                            recommended_action="Standardize all valid dates into ISO-8601 (YYYY-MM-DD) format.",
                            action_type="standardize_dates",
                            expected_impact=f"Standardizes chronological sorting and enables reliable time-series forecasting.",
                            risks_assumptions="Assumes unparseable dates can be resolved using standard datetime heuristics.",
                            is_selected_by_default=True,
                        )
                    )
                    cat_counts["invalid_dates"] += 1
                    sev_counts["high" if invalid_dates_count > 0 else "medium"] += 1

    # 8. Cross-Column Calculated Metric Consistency (e.g. Revenue = Units * Price)
    col_map = {c.lower(): c for c in df.columns}
    rev_col = col_map.get("revenue") or col_map.get("sales")
    units_col = col_map.get("units") or col_map.get("quantity") or col_map.get("qty")
    price_col = col_map.get("unit_price") or col_map.get("price")

    if rev_col and units_col and price_col:
        try:
            rev_s = pd.to_numeric(df[rev_col].astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
            units_s = pd.to_numeric(df[units_col].astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
            price_s = pd.to_numeric(df[price_col].astype(str).str.replace(",", "").str.replace("$", "").str.strip(), errors="coerce")
            
            valid_calc_mask = rev_s.notna() & units_s.notna() & price_s.notna() & (units_s > 0) & (price_s > 0)
            if valid_calc_mask.sum() >= 5:
                expected_rev = units_s[valid_calc_mask] * price_s[valid_calc_mask]
                actual_rev = rev_s[valid_calc_mask]
                rel_diff = np.abs(expected_rev - actual_rev) / np.maximum(expected_rev, 1e-6)
                mismatch_mask = rel_diff > 0.10  # >10% discrepancy
                mismatch_count = int(mismatch_mask.sum())
                
                if mismatch_count > 0:
                    pct = round((mismatch_count / total_rows) * 100, 2)
                    issues.append(
                        QualityIssue(
                            id="issue-calc-discrepancy",
                            category="calculation_anomaly",
                            severity="medium",
                            column=rev_col,
                            affected_rows_count=mismatch_count,
                            affected_percentage=pct,
                            sample_values=[f"Row {idx}: Actual {actual_rev.loc[idx]:.2f} vs Units*Price {expected_rev.loc[idx]:.2f}" for idx in mismatch_mask[mismatch_mask].index[:3]],
                            title=f"Calculation Discrepancy: '{rev_col}' vs '{units_col} * {price_col}'",
                            description=f"{mismatch_count} record(s) deviate by more than 10% from the expected calculation ({units_col} * {price_col}).",
                            why_it_matters="Discrepancies between total revenue and volume*rate indicate unrecorded discounts, tax additions, or calculation errors.",
                            recommended_action="Flag rows for audit or optionally recalculate Revenue to align with Units * Unit Price.",
                            action_type="audit_calculation",
                            expected_impact="Identifies accounting or formula discrepancies across transactions.",
                            risks_assumptions="Assumes discounts or tax surcharges explain discrepancies unless configured to recalculate.",
                            is_selected_by_default=False,
                        )
                    )
                    cat_counts["calculation_anomaly"] += 1
                    sev_counts["medium"] += 1
        except Exception:
            pass

    # Compute Comprehensive Quality Score (0 - 100)
    # Calculation formula:
    # 1. Completeness: % of total non-null cells (weight 35%)
    # 2. Uniqueness: % of non-duplicate rows (weight 25%)
    # 3. Validity: % of cells without formatting/negative issues (weight 25%)
    # 4. Consistency: % of columns without casing/date/type issues (weight 15%)
    total_cells = total_rows * total_cols
    total_missing_cells = sum(issue.affected_rows_count for issue in issues if issue.category == "missing_values")
    completeness_ratio = max(0.0, 1.0 - (total_missing_cells / total_cells)) if total_cells else 1.0

    dup_ratio = max(0.0, 1.0 - (dup_count / total_rows)) if total_rows else 1.0

    validity_issues = sum(issue.affected_rows_count for issue in issues if issue.category in ("numeric_formatting", "invalid_values"))
    validity_ratio = max(0.0, 1.0 - (validity_issues / max(total_cells, 1)))

    consistency_issues = len([i for i in issues if i.category in ("text_inconsistency", "invalid_dates")])
    consistency_ratio = max(0.0, 1.0 - (consistency_issues / max(total_cols, 1)))

    quality_score = (
        (completeness_ratio * 0.35)
        + (dup_ratio * 0.25)
        + (validity_ratio * 0.25)
        + (consistency_ratio * 0.15)
    ) * 100.0
    quality_score = round(max(5.0, min(100.0, quality_score)), 1)

    return issues, quality_score, cat_counts, sev_counts
