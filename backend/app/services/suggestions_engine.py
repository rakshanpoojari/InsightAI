from __future__ import annotations

import re
from typing import List, Optional
from app.models.dataset import DatasetColumn


def generate_dynamic_suggestions(columns: List[DatasetColumn], dataset_name: Optional[str] = None) -> List[str]:
    """
    Dynamically generates natural-language analytical questions strictly based
    on the actual columns and schema of the active dataset.
    """
    if not columns:
        return ["What is the total number of records?"]

    num_cols = [c for c in columns if c.inferred_type == "numeric"]
    cat_cols = [c for c in columns if c.inferred_type in ("categorical", "text")]
    date_cols = [c for c in columns if c.inferred_type == "datetime"]

    # If datetime not explicitly flagged, check column names like Date, Month, Time, Year
    if not date_cols:
        for c in columns:
            if any(k in c.name.lower() for k in ["date", "time", "month", "year", "period", "timestamp"]):
                date_cols.append(c)
                break

    # Prioritize business metrics
    def metric_priority(c: DatasetColumn) -> int:
        name = c.name.lower()
        if any(k in name for k in ["revenue", "sales", "turnover"]):
            return 0
        if any(k in name for k in ["profit", "margin", "income"]):
            return 1
        if any(k in name for k in ["cpi", "index", "price", "unit_price", "cost"]):
            return 2
        if any(k in name for k in ["units", "volume", "quantity", "qty", "count"]):
            return 3
        if any(k in name for k in ["rating", "score", "discount"]):
            return 4
        return 5

    num_cols.sort(key=metric_priority)

    # Prioritize categorical dimensions
    def dim_priority(c: DatasetColumn) -> int:
        name = c.name.lower()
        if any(k in name for k in ["product", "item", "sku"]):
            return 0
        if any(k in name for k in ["category", "segment", "department"]):
            return 1
        if any(k in name for k in ["region", "country", "territory", "city", "state", "location"]):
            return 2
        if any(k in name for k in ["customer", "client", "buyer"]):
            return 3
        if any(k in name for k in ["channel", "store"]):
            return 4
        return 5

    cat_cols.sort(key=dim_priority)

    suggestions: List[str] = []

    primary_metric = num_cols[0] if len(num_cols) > 0 else None
    secondary_metric = num_cols[1] if len(num_cols) > 1 else None
    tertiary_metric = num_cols[2] if len(num_cols) > 2 else None

    primary_dim = cat_cols[0] if len(cat_cols) > 0 else None
    secondary_dim = cat_cols[1] if len(cat_cols) > 1 else None
    date_col = date_cols[0] if len(date_cols) > 0 else None

    # 1. Highest ranking metric by dimension (e.g. Which Product has the highest Revenue?)
    if primary_dim and primary_metric:
        suggestions.append(f"Which {primary_dim.name} has the highest {primary_metric.name}?")

    # 2. Aggregation by secondary dimension (e.g. What is the average Profit by Category?)
    if secondary_dim and (secondary_metric or primary_metric):
        metric = secondary_metric or primary_metric
        suggestions.append(f"What is the average {metric.name} by {secondary_dim.name}?")
    elif primary_dim and primary_metric:
        suggestions.append(f"Show {primary_metric.name} by {primary_dim.name}")

    # 3. Highest units / volume / dimension ranking
    units_metric = next((c for c in num_cols if any(k in c.name.lower() for k in ["unit", "volume", "qty", "quantity"])), None)
    region_dim = next((c for c in cat_cols if any(k in c.name.lower() for k in ["region", "area", "territory", "city", "location"])), None)
    if region_dim and units_metric:
        suggestions.append(f"Which {region_dim.name} has the highest {units_metric.name}?")
    elif primary_dim and secondary_metric:
        suggestions.append(f"Which {primary_dim.name} has the highest {secondary_metric.name}?")

    # 4. Rating, Margin, or Lowest metric question
    rating_metric = next((c for c in num_cols if any(k in c.name.lower() for k in ["rating", "margin", "discount", "price", "cost"])), None)
    if primary_dim and rating_metric and rating_metric != primary_metric:
        verb = "lowest" if "discount" not in rating_metric.name.lower() else "highest"
        suggestions.append(f"Which {primary_dim.name} has the {verb} {rating_metric.name}?")
    elif secondary_dim and primary_metric:
        suggestions.append(f"Show {primary_metric.name} by {secondary_dim.name}")

    # 5. Correlation / Relationship question (e.g. What is the relationship between Revenue and Units?)
    if primary_metric and secondary_metric:
        suggestions.append(f"What is the relationship between {primary_metric.name} and {secondary_metric.name}?")

    # 6. Temporal trend question (e.g. Show Revenue trends over Date)
    if date_col and primary_metric:
        suggestions.append(f"Show {primary_metric.name} trends over {date_col.name}")

    # 7. Total overall metric (e.g. What is the total Revenue?)
    if primary_metric:
        suggestions.append(f"What is the total {primary_metric.name}?")

    # Fallback to total record count if list is short
    if len(suggestions) < 5:
        suggestions.append("What is the total number of records?")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            deduped.append(s)

    return deduped[:7]
