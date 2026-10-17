from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.models.dataset import Dataset, DatasetColumn
from app.services import gemini_service, sql_engine

logger = logging.getLogger("insightai.nl_query")


SYNONYM_MAP = {
    "revenue": ["sales", "revenue", "revenues", "income", "turnover"],
    "sales": ["sales", "revenue", "revenues", "income", "turnover"],
    "turnover": ["sales", "revenue", "revenues", "income"],
    "profit": ["profit", "profits", "margin", "earnings", "net_income"],
    "margin": ["profit", "margin", "profit_margin", "profit_margin_pct"],
    "cost": ["cost", "costs", "expense", "expenses", "spend"],
    "price": ["unit_price", "price", "pricing"],
    "discount": ["discount", "discount_pct", "markdown"],
    "units": ["units", "quantity", "qty", "volume", "items"],
    "quantity": ["units", "quantity", "qty", "volume", "items"],
    "volume": ["units", "quantity", "qty", "volume"],
    "product": ["product", "item", "sku", "merchandise", "good"],
    "category": ["category", "segment", "department", "genre", "type"],
    "region": ["region", "territory", "area", "location", "zone", "city", "state", "country"],
    "customer": ["customer", "client", "buyer", "account", "customer_type"],
    "channel": ["channel", "store", "platform", "source"],
}

STOP_WORDS = {
    "what", "is", "the", "a", "an", "of", "by", "for", "in", "to", "and", "between",
    "show", "get", "which", "how", "many", "tell", "me", "find", "give", "with",
}


def _match_column(
    words: List[str], target_type: str, columns: List[DatasetColumn], exclude_names: Optional[List[str]] = None
) -> Optional[DatasetColumn]:
    exclude_names = exclude_names or []
    candidates = [c for c in columns if c.inferred_type == target_type and c.name not in exclude_names]
    content_words = [w for w in words if w not in STOP_WORDS]

    # 1. Exact name match
    for col in candidates:
        col_norm = col.name.lower().replace("_", "")
        for w in content_words:
            if w == col_norm or w == col.name.lower():
                return col

    # 2. Token-level synonym match
    for col in candidates:
        col_norm = col.name.lower().replace("_", "")
        for w in content_words:
            synonyms = SYNONYM_MAP.get(w, [])
            for syn in synonyms:
                syn_clean = syn.lower().replace("_", "")
                if syn_clean == col_norm or syn.lower() == col.name.lower():
                    return col

    # 3. Substring match
    for col in candidates:
        col_norm = col.name.lower().replace("_", "")
        for w in content_words:
            if len(w) >= 4 and (w in col_norm or col_norm in w):
                return col

    return None


def generate_sql_from_heuristics(
    question: str, table_name: str, columns: List[DatasetColumn]
) -> Tuple[str, str]:
    q_lower = question.lower().strip()
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", q_lower)

    num_cols = [c for c in columns if c.inferred_type == "numeric"]
    cat_cols = [c for c in columns if c.inferred_type in ("categorical", "text")]
    date_cols = [c for c in columns if c.inferred_type == "datetime"]

    # Pattern 1: Row count / size
    if any(phrase in q_lower for phrase in ["how many rows", "how many records", "total count", "total records", "number of rows"]):
        sql = f'SELECT COUNT(*) AS "total_records" FROM "{table_name}"'
        summary = "Calculated total number of records in the dataset."
        return sql, summary

    # Pattern 2: Pearson Correlation via DuckDB
    if any(term in words for term in ["correlation", "corr", "correlate", "relationship"]):
        m1 = _match_column(words, "numeric", columns)
        m2 = _match_column(words, "numeric", columns, exclude_names=[m1.name] if m1 else [])
        if not m1 and len(num_cols) >= 1:
            m1 = num_cols[0]
        if not m2 and len(num_cols) >= 2:
            m2 = [c for c in num_cols if c.name != (m1.name if m1 else "")][0]
        if m1 and m2:
            sql = (
                f'SELECT ROUND(CORR("{m1.name}", "{m2.name}"), 4) AS "correlation_{m1.name}_{m2.name}" '
                f'FROM "{table_name}" '
                f'WHERE "{m1.name}" IS NOT NULL AND "{m2.name}" IS NOT NULL'
            )
            summary = f"Calculated Pearson correlation coefficient between {m1.name} and {m2.name} using DuckDB."
            return sql, summary

    # Match target numeric metric
    target_metric = _match_column(words, "numeric", columns)

    # Match target dimension (categorical or text)
    target_dim = _match_column(words, "categorical", columns) or _match_column(words, "text", columns)
    if not target_dim and any(t in q_lower for t in ["time", "date", "month", "trend", "daily", "timeline", "yearly", "year"]):
        if date_cols:
            target_dim = date_cols[0]

    # If query asks "Which <dimension> performs best/worst" without naming a metric
    if target_dim and not target_metric:
        for pref in ["sales", "revenue", "profit", "units"]:
            for col in num_cols:
                if pref in col.name.lower():
                    target_metric = col
                    break
            if target_metric:
                break
        if not target_metric and num_cols:
            target_metric = num_cols[0]

    # Default metric if none found but numeric columns exist
    if not target_metric and num_cols:
        target_metric = num_cols[0]

    # Check for aggregation type
    agg = "SUM"
    agg_label = "Total"
    if any(w in words for w in ["average", "avg", "mean"]):
        agg = "AVG"
        agg_label = "Average"
    elif any(w in words for w in ["minimum", "lowest", "min", "bottom"]) and not any(w in words for w in ["highest", "best"]):
        agg = "MIN"
        agg_label = "Minimum"
    elif any(w in words for w in ["maximum", "highest", "max", "top"]) and not target_dim:
        agg = "MAX"
        agg_label = "Maximum"
    elif any(w in words for w in ["count", "number", "how many"]):
        agg = "COUNT"
        agg_label = "Count"

    # Limit detection
    limit_match = re.search(r"\b(?:top|first|limit)\s+(\d+)\b", q_lower)
    limit_num = int(limit_match.group(1)) if limit_match else None

    # Ranking query ("Which X has highest/lowest" or "Which X performs best")
    is_ranking = any(w in words for w in ["which", "what", "who"]) and any(
        w in words for w in ["highest", "best", "top", "lowest", "worst", "bottom"]
    )
    order_dir = "ASC" if any(w in words for w in ["lowest", "worst", "bottom", "least"]) else "DESC"

    if is_ranking and target_dim and target_metric:
        limit_val = limit_num or 1
        sql = (
            f'SELECT "{target_dim.name}", ROUND({agg}("{target_metric.name}"), 2) AS "{agg_label}_{target_metric.name}" '
            f'FROM "{table_name}" '
            f'WHERE "{target_dim.name}" IS NOT NULL '
            f'GROUP BY "{target_dim.name}" '
            f'ORDER BY "{agg_label}_{target_metric.name}" {order_dir} LIMIT {limit_val}'
        )
        verb = "top-performing" if order_dir == "DESC" else "lowest-performing"
        summary = f"Identified {verb} {target_dim.name} by {agg_label.lower()} {target_metric.name}."
        return sql, summary

    # Pattern 3: Dimension + Metric aggregation (e.g. Total Sales by Product, Sales by Category)
    if target_metric and target_dim:
        limit_clause = f" LIMIT {limit_num}" if limit_num else " LIMIT 15"
        sql = (
            f'SELECT "{target_dim.name}", ROUND({agg}("{target_metric.name}"), 2) AS "{agg_label}_{target_metric.name}" '
            f'FROM "{table_name}" '
            f'WHERE "{target_dim.name}" IS NOT NULL '
            f'GROUP BY "{target_dim.name}" '
            f'ORDER BY "{agg_label}_{target_metric.name}" {order_dir}{limit_clause}'
        )
        summary = f"Calculated {agg_label.lower()} {target_metric.name} broken down by {target_dim.name}."
        return sql, summary

    # Pattern 4: Aggregation of single metric (e.g. Total Sales, What is the total revenue)
    if target_metric:
        sql = f'SELECT ROUND({agg}("{target_metric.name}"), 2) AS "{agg_label}_{target_metric.name}" FROM "{table_name}"'
        summary = f"Calculated overall {agg_label.lower()} for {target_metric.name}."
        return sql, summary

    # Pattern 5: Distinct categorical values (e.g. list products, regions)
    if target_dim:
        sql = f'SELECT DISTINCT "{target_dim.name}" FROM "{table_name}" WHERE "{target_dim.name}" IS NOT NULL LIMIT 20'
        summary = f"Retrieved unique values for {target_dim.name}."
        return sql, summary

    # Fallback: General preview
    limit = limit_num or 10
    sql = f'SELECT * FROM "{table_name}" LIMIT {limit}'
    summary = f"Retrieved top {limit} rows from dataset."
    return sql, summary


def generate_sql_from_llm(
    question: str, table_name: str, columns: List[DatasetColumn]
) -> Optional[Tuple[str, str]]:
    """Generates SQL via Gemini or OpenAI if API keys are available in environment."""
    # 1. Try Gemini first if configured
    if gemini_service.is_gemini_configured():
        try:
            gemini_res = gemini_service.generate_sql_intent_with_gemini(question, table_name, columns)
            if gemini_res:
                sql, summary = gemini_res
                # Strictly validate that generated SQL is read-only and safe
                sql_engine.validate_sql(sql)
                return sql, summary
        except Exception as e:
            logger.warning(f"Gemini SQL generation failed or query was rejected by safety validator: {e}")

    # 2. Try OpenAI fallback if configured
    if settings.openai_api_key:
        schema_desc = "\n".join(
            [f"- {c.name} ({c.inferred_type}): sample values {c.sample_values}" for c in columns[:25]]
        )

        prompt = f"""You are an expert SQL assistant for InsightAI.
Database Table: "{table_name}"
Columns:
{schema_desc}

User Question: "{question}"

Instructions:
1. Generate a valid, safe, read-only SELECT SQL query for SQLite/DuckDB.
2. Return ONLY valid JSON with keys:
   - "sql": the executable SQL query enclosed in double quotes for table and column names
   - "summary": a one-sentence human explanation of what the query calculates

JSON Response:"""
        try:
            res = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
                timeout=12.0,
            )
            if res.status_code == 200:
                data = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(data)
                sql = parsed.get("sql")
                summary = parsed.get("summary")
                if sql:
                    sql_engine.validate_sql(sql)
                    return sql, summary
        except Exception as e:
            logger.warning(f"OpenAI SQL generation failed, falling back to heuristics: {e}")

    return None


def translate_question_to_sql(
    question: str, dataset: Dataset, columns: List[DatasetColumn]
) -> Tuple[str, str]:
    # 1. Try LLM if configured
    llm_result = generate_sql_from_llm(question, dataset.storage_table_name, columns)
    if llm_result:
        return llm_result

    # 2. Schema-aware deterministic heuristics
    return generate_sql_from_heuristics(question, dataset.storage_table_name, columns)
