from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.schemas import ChartConfig, QueryResult

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|EXEC|EXECUTE|VACUUM|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> None:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("Empty SQL query provided.")

    if not cleaned.lower().startswith("select") and not cleaned.lower().startswith("with"):
        raise ValueError("Only SELECT and WITH (CTE) queries are permitted for safety.")

    # Match forbidden keywords
    match = FORBIDDEN_SQL_PATTERN.search(cleaned)
    if match:
        raise ValueError(f"Prohibited SQL operation detected: '{match.group(0)}'. Queries must be strictly read-only.")


def execute_query(engine: Engine, table_name: str, sql: str) -> QueryResult:
    validate_sql(sql)

    # Ensure table name is safely referenced
    # Allow user/engine to refer to either the logical table or physical table_name
    normalized_sql = sql.strip().rstrip(";")
    # Replace generic names like "data", "dataset", "sales", "table" if table_name not directly mentioned
    pattern = re.compile(r"\bFROM\s+([`\"'\[]?[a-zA-Z0-9_]+[`\"'\]]?)", re.IGNORECASE)

    def table_replacer(match):
        raw_target = match.group(1).strip("`\"'[]")
        if raw_target.lower() in ("data", "dataset", "current_dataset", "records", "tbl", "df"):
            return f'FROM "{table_name}"'
        return match.group(0)

    exec_sql = pattern.sub(table_replacer, normalized_sql)

    # Load from persistent SQLite storage into DataFrame
    df = pd.read_sql(f'SELECT * FROM "{table_name}"', con=engine)

    # Execute analytical query using DuckDB vectorized in-memory engine
    start_time = time.perf_counter()
    con = duckdb.connect(database=":memory:")
    try:
        con.register(table_name, df)
        con.register("dataset", df)
        con.register("data", df)
        con.register("tbl", df)
        try:
            res_df = con.execute(exec_sql).fetchdf()
        except Exception:
            res_df = con.execute(normalized_sql).fetchdf()
    except Exception as e:
        raise ValueError(f"DuckDB execution error: {e}")
    finally:
        con.close()

    execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    columns = list(res_df.columns)

    # Sanitize records to native types for compliant JSON serialization
    rows: List[Dict[str, Any]] = []
    for r in res_df.to_dict(orient="records"):
        item: Dict[str, Any] = {}
        for k, v in r.items():
            if v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)):
                item[k] = None
            elif isinstance(v, (np.integer, int)):
                item[k] = int(v)
            elif isinstance(v, (np.floating, float)):
                item[k] = round(float(v), 4)
            elif isinstance(v, (pd.Timestamp,)):
                item[k] = v.isoformat()
            else:
                item[k] = v
        rows.append(item)

    chart_cfg = infer_chart_configuration(columns, rows)

    return QueryResult(
        sql=exec_sql,
        columns=columns,
        rows=rows,
        total_rows=len(rows),
        execution_time_ms=execution_time_ms,
        chart_config=chart_cfg,
    )


def infer_chart_configuration(columns: List[str], rows: List[Dict[str, Any]]) -> Optional[ChartConfig]:
    if not rows or not columns:
        return None

    if len(rows) == 1 and len(columns) == 1:
        col = columns[0]
        return ChartConfig(
            chart_type="metric",
            title=f"Total {col}",
            series_keys=[col],
        )

    df_sample = pd.DataFrame(rows[:50])
    num_cols = []
    cat_cols = []
    date_cols = []

    for c in columns:
        s = df_sample[c].dropna()
        if s.empty:
            continue
        if pd.api.types.is_numeric_dtype(s):
            num_cols.append(c)
        elif pd.api.types.is_datetime64_any_dtype(s) or (
            s.astype(str).str.match(r"^\d{4}-\d{2}|^\d{1,2}/\d{1,2}").mean() > 0.6
        ):
            date_cols.append(c)
        else:
            cat_cols.append(c)

    # Rule 1: Date column + numeric column -> Line or Area chart
    if date_cols and num_cols:
        return ChartConfig(
            chart_type="line",
            x_axis=date_cols[0],
            y_axis=num_cols[0],
            series_keys=num_cols[:3],
            title=f"{', '.join(num_cols[:3])} over {date_cols[0]}",
        )

    # Rule 2: Low-cardinality categorical (<=6 items) + 1 numeric -> Pie / Donut
    if cat_cols and num_cols and len(rows) <= 6:
        return ChartConfig(
            chart_type="donut",
            x_axis=cat_cols[0],
            y_axis=num_cols[0],
            series_keys=[num_cols[0]],
            title=f"Distribution of {num_cols[0]} by {cat_cols[0]}",
        )

    # Rule 3: Categorical + numeric -> Bar chart
    if cat_cols and num_cols:
        return ChartConfig(
            chart_type="bar",
            x_axis=cat_cols[0],
            y_axis=num_cols[0],
            series_keys=num_cols[:3],
            title=f"{', '.join(num_cols[:3])} by {cat_cols[0]}",
        )

    # Rule 4: Multiple numeric columns -> Bar comparison
    if len(num_cols) >= 2 and cat_cols:
        return ChartConfig(
            chart_type="bar",
            x_axis=cat_cols[0],
            y_axis=num_cols[0],
            series_keys=num_cols[:4],
            title=f"Comparison of metrics by {cat_cols[0]}",
        )

    # Default fallback
    if len(columns) >= 2:
        return ChartConfig(
            chart_type="bar",
            x_axis=columns[0],
            y_axis=columns[1],
            series_keys=[columns[1]],
            title=f"{columns[1]} by {columns[0]}",
        )

    return None
