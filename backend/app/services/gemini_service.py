from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.dataset import Dataset, DatasetColumn

logger = logging.getLogger("insightai.gemini")

# Input constraints
MAX_QUESTION_LENGTH = 500
MAX_RESULT_ROWS_FOR_AI = 15

# Lazy client instance
_gemini_client = None


def is_gemini_configured() -> bool:
    """Returns True if a non-empty Gemini API key is configured."""
    return bool(settings.gemini_api_key and settings.gemini_api_key.strip())


def get_gemini_client():
    """Safely initializes and returns the official google-genai Client."""
    global _gemini_client
    if not is_gemini_configured():
        return None

    if _gemini_client is not None:
        return _gemini_client

    try:
        from google import genai
        from google.genai import types

        # Initialize official google-genai client with 15s timeout
        http_opts = types.HttpOptions(timeout=15.0)
        _gemini_client = genai.Client(api_key=settings.gemini_api_key.strip(), http_options=http_opts)
        logger.info(f"Initialized Gemini client with model '{settings.gemini_model}'")
        return _gemini_client
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")
        return None


def explain_query_results(
    question: str,
    dataset_name: str,
    columns: List[DatasetColumn],
    sql: str,
    rows: List[Dict[str, Any]],
    total_rows: int,
    execution_time_ms: float,
) -> Optional[Dict[str, Any]]:
    """
    Asks Gemini to explain verified query results in plain language.
    Does NOT send raw row-level dataset: sends only minimal schema and top aggregated results.
    """
    client = get_gemini_client()
    if not client:
        return None

    # Length guardrail
    safe_question = question.strip()[:MAX_QUESTION_LENGTH]

    # Minimal schema: only names and types (no raw data)
    schema_summary = [{"name": c.name, "type": c.inferred_type} for c in columns[:25]]

    # Sample of aggregated query results
    sample_rows = rows[:MAX_RESULT_ROWS_FOR_AI]

    prompt = f"""You are an expert Data Analyst & Business Intelligence Copilot for InsightAI.
Analyze the following verified database query execution and explain the findings clearly to business stakeholders.

Context:
- Dataset: "{dataset_name}"
- Available Columns (Schema Metadata Only): {json.dumps(schema_summary)}
- User Question: "{safe_question}"
- Executed SQL (Read-Only DuckDB/SQLite): {sql}
- Query Execution: {total_rows} row(s) returned in {execution_time_ms:.1f}ms
- Verified Query Results (First {len(sample_rows)} rows):
{json.dumps(sample_rows, default=str)}

STRICT OPERATIONAL RULES:
1. Base all facts, numbers, and statements STRICTLY on the provided verified query results.
2. NEVER fabricate, hallucinate, or estimate numbers, percentages, or metrics.
3. If correlation is present, label it strictly as correlation; NEVER imply or state causation.
4. Clearly distinguish computed mathematical facts from strategic hypotheses or recommendations.
5. If the query results do not provide enough evidence to fully answer the question, state that clearly.
6. Return a valid JSON object matching the schema below.

JSON Schema:
{{
  "answer": "Concise 2-3 sentence executive answer explaining the verified query results directly.",
  "supporting_figures": ["Key metric with value, e.g., 'Total Profit: $125,400.00'", "Top Category: Electronics (45.2%)"],
  "relevant_columns": ["column_name_1", "column_name_2"],
  "insights": ["Actionable business hypothesis or strategic suggestion based on these findings."],
  "chart_suggestion": {{
    "chart_type": "bar | line | area | pie",
    "x_axis": "column_name",
    "y_axis": "column_name",
    "title": "Chart Title"
  }}
}}
"""

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
            response_mime_type="application/json",
            system_instruction="You are InsightAI's analytical copilot. Output only verified facts and valid JSON.",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            return None

        data = json.loads(response.text)
        if not isinstance(data, dict):
            return None

        return {
            "ai_explanation": str(data.get("answer", "")).strip(),
            "ai_supporting_figures": [str(x) for x in data.get("supporting_figures", []) if x],
            "ai_relevant_columns": [str(x) for x in data.get("relevant_columns", []) if x],
            "ai_insights": [str(x) for x in data.get("insights", []) if x],
            "ai_provider": model_name,
            "chart_suggestion": data.get("chart_suggestion"),
        }
    except Exception as e:
        logger.warning(f"Gemini query explanation failed (falling back to deterministic summary): {e}")
        return None


def enhance_insights_with_gemini(
    dataset_name: str,
    computed_insights: List[Dict[str, Any]],
    correlation_matrix: Optional[Dict[str, Dict[str, float]]],
) -> Optional[Dict[str, Any]]:
    """
    Asks Gemini to explain deterministically computed findings and provide concise recommendations.
    All underlying metrics are already calculated by Python services.
    """
    client = get_gemini_client()
    if not client:
        return None

    # Strip any heavy non-essential data, send only mathematical signals
    clean_insights = []
    for inc in computed_insights:
        clean_insights.append({
            "id": inc.get("id"),
            "category": inc.get("category"),
            "impact": inc.get("impact"),
            "title": inc.get("title"),
            "metric": inc.get("metric"),
            "description": inc.get("description"),
            "recommendation": inc.get("recommendation"),
            "affected_columns": inc.get("affected_columns", []),
        })

    prompt = f"""You are an executive BI Data Strategist for InsightAI.
You are reviewing deterministically computed statistical findings for dataset "{dataset_name}".

Verified Mathematical Findings:
{json.dumps(clean_insights, indent=2)}

STRICT OPERATIONAL RULES:
1. Every insight is backed by verified mathematics. DO NOT invent, alter, or hallucinate numbers or metrics.
2. Label correlation as correlation, NEVER causation.
3. Provide a concise, cohesive executive summary synthesizing these findings for leadership (2-3 sentences).
4. For each insight card, provide an executive explanation and an actionable recommendation. If evidence is insufficient for a recommendation, state 'Insufficient evidence to prescribe specific action.'
5. Return a valid JSON object matching the schema below.

JSON Schema:
{{
  "executive_summary": "Executive summary synthesizing the verified findings.",
  "enhanced_insights": [
    {{
      "id": "matching insight id",
      "executive_title": "Clear strategic title",
      "explanation": "Executive narrative explaining the verified metric.",
      "recommendation": "Concrete, actionable next step.",
      "affected_columns": ["col1", "col2"]
    }}
  ]
}}
"""

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1500,
            response_mime_type="application/json",
            system_instruction="You are InsightAI's executive insights advisor. You communicate with strict factual accuracy.",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            return None

        data = json.loads(response.text)
        if not isinstance(data, dict):
            return None

        return {
            "executive_summary": data.get("executive_summary"),
            "enhanced_insights": data.get("enhanced_insights", []),
            "ai_provider": model_name,
        }
    except Exception as e:
        logger.warning(f"Gemini insights enhancement failed (falling back to deterministic insights): {e}")
        return None


def generate_sql_intent_with_gemini(
    question: str,
    table_name: str,
    columns: List[DatasetColumn],
) -> Optional[Tuple[str, str]]:
    """
    Uses Gemini to propose a candidate SQL query plan for complex questions.
    Returns (sql, summary) if successful and passes strict validation, else None.
    """
    client = get_gemini_client()
    if not client:
        return None

    safe_question = question.strip()[:MAX_QUESTION_LENGTH]
    schema_desc = "\n".join(
        [f"- {c.name} ({c.inferred_type})" for c in columns[:30]]
    )

    prompt = f"""You are a specialized SQL planner for InsightAI.
Database Table: "{table_name}"
Columns:
{schema_desc}

User Question: "{safe_question}"

Instructions:
1. Generate a valid, strictly read-only SELECT query for DuckDB/SQLite.
2. Only use double quotes for column and table names: "{table_name}", "column_name".
3. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, PRAGMA or non-SELECT queries.
4. Always include a sensible LIMIT (default 15 for grouping/aggregation, 10 for raw listings) unless computing an overall scalar aggregate.
5. Return ONLY a JSON object with:
   - "sql": the executable SELECT query
   - "summary": one-sentence human explanation of what the query calculates

JSON Response:"""

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=500,
            response_mime_type="application/json",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            return None

        data = json.loads(response.text)
        sql = data.get("sql")
        summary = data.get("summary")
        if not sql or not summary:
            return None

        return str(sql).strip(), str(summary).strip()
    except Exception as e:
        logger.warning(f"Gemini SQL intent generation failed: {e}")
        return None


def explain_data_quality_report(
    dataset_name: str,
    issues: List[Dict[str, Any]],
    quality_score: float,
) -> Optional[Dict[str, Any]]:
    """
    Asks Gemini to explain data quality issues and recommendations in plain language.
    Does NOT send raw row-level data: sends only detected issue metadata and sample values.
    Falls back gracefully to a deterministic quality assessment if Gemini is unavailable.
    """
    def _fallback_summary() -> Dict[str, Any]:
        high_count = sum(1 for i in issues if i.get("severity") == "high")
        med_count = sum(1 for i in issues if i.get("severity") == "medium")
        total = len(issues)
        if quality_score >= 85:
            summary = (
                f"Dataset '{dataset_name}' exhibits strong data hygiene with a reliability score of {quality_score:.1f}%. "
                f"Identified {total} minor item(s). The dataset is well-structured and ready for downstream analytics and predictive modeling."
            )
        elif quality_score >= 60:
            summary = (
                f"Dataset '{dataset_name}' exhibits moderate data quality ({quality_score:.1f}% reliability) with {total} detected issue(s), "
                f"including {high_count} high-severity and {med_count} medium-severity concern(s). Addressing missing values and format inconsistencies "
                "prior to executive dashboard reporting is recommended."
            )
        else:
            summary = (
                f"Dataset '{dataset_name}' requires data hygiene intervention ({quality_score:.1f}% reliability). "
                f"Detected {total} issue(s) ({high_count} high severity) across schema dimensions. Review and apply recommended transformations "
                "to prevent skewed business reporting."
            )
        return {
            "ai_summary": summary,
            "issue_enhancements": [],
            "ai_provider": "InsightAI Rule Engine (Deterministic Fallback)",
        }

    client = get_gemini_client()
    if not client:
        return _fallback_summary()

    minimal_issues = []
    for iss in issues[:20]:
        minimal_issues.append({
            "id": iss.get("id"),
            "category": iss.get("category"),
            "severity": iss.get("severity"),
            "column": iss.get("column"),
            "affected_rows_count": iss.get("affected_rows_count"),
            "sample_values": iss.get("sample_values", [])[:3],
            "title": iss.get("title"),
        })

    prompt = f"""You are an expert Data Quality & Governance Analyst for InsightAI.
Review the following deterministic data quality audit results for dataset "{dataset_name}".
Overall Quality Score: {quality_score:.1f}/100

Detected Issues:
{json.dumps(minimal_issues, indent=2)}

STRICT OPERATIONAL RULES:
1. Base all explanations strictly on the provided audit findings. Do NOT invent new numbers or phantom columns.
2. Provide a 2-3 sentence executive summary explaining the overall data hygiene and readiness for analytics.
3. For each issue, provide a brief plain-language explanation of why it matters for business analysis, and what assumptions/risks exist if corrected.
4. Return a valid JSON object matching the schema below.

JSON Schema:
{{
  "ai_summary": "Executive summary of dataset hygiene and readiness for analytics.",
  "issue_enhancements": [
    {{
      "id": "matching issue id",
      "why_it_matters": "Business consequence if left unaddressed.",
      "risks_assumptions": "Assumptions made when applying standard corrections."
    }}
  ]
}}
"""

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1500,
            response_mime_type="application/json",
            system_instruction="You are InsightAI's data quality advisor. You communicate with strict factual accuracy.",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            return _fallback_summary()

        data = json.loads(response.text)
        if not isinstance(data, dict):
            return _fallback_summary()

        return {
            "ai_summary": data.get("ai_summary") or _fallback_summary()["ai_summary"],
            "issue_enhancements": data.get("issue_enhancements", []),
            "ai_provider": model_name,
        }
    except Exception as e:
        logger.warning(f"Gemini data quality explanation failed: {e}")
        return _fallback_summary()


def explain_forecast(forecast_metrics: Dict[str, Any], is_cpi: bool = False) -> Dict[str, Any]:
    """
    Generates plain-language executive explanation, historical patterns,
    uncertainty analysis, business implications, and actionable recommendations
    based strictly on verified forecasting metrics.
    """
    def _deterministic_fallback() -> Dict[str, Any]:
        if is_cpi:
            mode_label = forecast_metrics.get("mode_label", "CPI / Price Forecast")
            curr = forecast_metrics.get("current_index", 0.0)
            change_pct = forecast_metrics.get("projected_change_pct", 0.0)
            annualized = forecast_metrics.get("annualized_rate_pct", 0.0)
            volatility = forecast_metrics.get("volatility_pct", 0.0)
            model_name = forecast_metrics.get("model_name", "Holt's Exponential Smoothing")
            scope = forecast_metrics.get("selected_dimension_value", "All")
            horizon = forecast_metrics.get("horizon_months", 6)
            fit_mape = forecast_metrics.get("fit_mape", 0.0)
            purchasing = forecast_metrics.get("purchasing_recommendation", "Maintain structured procurement.")

            direction = "Upward" if change_pct > 1.0 else ("Downward" if change_pct < -1.0 else "Stable")

            summary = (
                f"The {mode_label} for '{scope}' is projected to follow an {direction.lower()} trajectory, "
                f"yielding an expected {change_pct:+.1f}% change (annualized rate of {annualized:+.1f}%) "
                f"over the next {horizon} months from current level of {curr:.2f}."
            )

            hist_patterns = (
                f"Historical observations ({forecast_metrics.get('historical_observations', 0)} periods) demonstrate a "
                f"coefficient of variation of {volatility:.1f}%, signifying {'elevated price fluctuation' if volatility > 15 else 'moderate variance' if volatility > 5 else 'high price stability'}. "
                f"The highest historical growth category was '{forecast_metrics.get('highest_growth_category', 'All')}'; "
                f"lowest was '{forecast_metrics.get('lowest_growth_category', 'All')}'."
            )

            assumptions = (
                f"Model relies on {model_name} with an empirical fit MAPE of {fit_mape:.1f}%. "
                "Prediction intervals expand over time to account for compound variance and macro shocks."
            )

            implications = (
                f"Procurement analysis indicates: {purchasing} "
                f"Organizations budgeting for '{scope}' should adjust forward projections by {annualized:+.1f}% to insulate margins."
            )

            recs = [
                f"Align forward supplier contracts according to the {direction.lower()} price trajectory.",
                f"Buffer inventory or budget contingency by {abs(annualized):.1f}% for anticipated rate movement.",
                f"Re-audit price indices quarterly against actual vendor invoices.",
            ]

            return {
                "summary": summary,
                "historical_patterns": hist_patterns,
                "assumptions_uncertainty": assumptions,
                "business_implications": implications,
                "recommendations": recs,
                "model_used": model_name,
                "trend_direction": direction,
                "projected_change_pct": round(float(change_pct), 2),
                "confidence_level": f"95% Prediction Interval (MAPE: {fit_mape:.1f}%)",
                "ai_provider": "InsightAI Forecasting Engine (Deterministic Fallback)",
            }
        else:
            target = forecast_metrics.get("target_column", "Target Metric")
            date_col = forecast_metrics.get("date_column", "Date")
            horizon = forecast_metrics.get("horizon", 14)
            direction = forecast_metrics.get("trend_direction", "Stable")
            growth = forecast_metrics.get("expected_growth_pct", 0.0)
            r2 = forecast_metrics.get("r_squared", 0.0)
            hist_avg = forecast_metrics.get("avg_historical", 0.0)
            proj_avg = forecast_metrics.get("projected_horizon_avg", 0.0)

            summary = (
                f"Projected {horizon}-period trajectory for '{target}' along '{date_col}' indicates an {direction.lower()} trend "
                f"with an expected shift of {growth:+.1f}%, moving from historical average of {hist_avg:,.2f} to horizon average of {proj_avg:,.2f}."
            )

            hist_patterns = (
                f"Historical sequence displays a linear regression slope of {forecast_metrics.get('slope', 0.0):+.3f} per period "
                f"with goodness-of-fit R² = {r2:.2f} across the historical baseline."
            )

            assumptions = (
                "The projection assumes continuity of baseline trend parameters without sudden systemic disruptions. "
                "95% prediction intervals widen outward proportional to the square root of horizon distance."
            )

            implications = (
                f"Operations should {'scale capacity and staffing to capture expected growth' if growth > 5 else 'review cost levers and pipeline generation' if growth < -5 else 'maintain current capacity allocation'} "
                f"to support projected {target.lower()} levels."
            )

            recs = [
                f"Incorporate the {growth:+.1f}% anticipated change into upcoming financial and operational forecasts.",
                "Establish milestone checkpoints to compare actual metric outcomes against the 95% confidence bounds.",
                "Review sensitivity to underlying drivers if metric approaches upper or lower uncertainty bands.",
            ]

            return {
                "summary": summary,
                "historical_patterns": hist_patterns,
                "assumptions_uncertainty": assumptions,
                "business_implications": implications,
                "recommendations": recs,
                "model_used": "Linear Trend Regression with 95% Confidence Bounds",
                "trend_direction": direction,
                "projected_change_pct": round(float(growth), 2),
                "confidence_level": f"95% Confidence Interval (R²: {r2:.2f})",
                "ai_provider": "InsightAI Forecasting Engine (Deterministic Fallback)",
            }

    client = get_gemini_client()
    if not client:
        return _deterministic_fallback()

    prompt = f"""You are an executive Chief Analytics Officer and Senior Econometrician for InsightAI.
Review the following verified forecast statistical results:
Forecast Context:
- Domain: {'Consumer Price Index & Macroeconomics' if is_cpi else 'General Business Time-Series'}
- Verified Metrics:
{json.dumps(forecast_metrics, indent=2)}

STRICT OPERATIONAL RULES:
1. Base all narrative strictly on the provided verified metrics. Do NOT alter any figures, dates, or calculations.
2. Provide an executive plain-language summary (2-3 sentences).
3. Outline key historical patterns (trend direction, volatility, cycles).
4. Explain model assumptions and reason for expanding confidence bands.
5. Detail business implications for leadership (inventory, pricing, budgeting, staffing).
6. Provide 2-4 concrete, numbered recommendations.
7. Return a valid JSON object matching the schema below.

JSON Schema:
{{
  "summary": "Executive plain-language summary.",
  "historical_patterns": "Key patterns observed in historical baseline.",
  "assumptions_uncertainty": "Assumptions made and uncertainty band behavior.",
  "business_implications": "Actionable takeaways for business leadership.",
  "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
}}
"""

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1500,
            response_mime_type="application/json",
            system_instruction="You are InsightAI's quantitative forecaster. You explain statistical results with precision and clarity.",
        )

        model_name = settings.gemini_model or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            return _deterministic_fallback()

        data = json.loads(response.text)
        if not isinstance(data, dict):
            return _deterministic_fallback()

        fallback = _deterministic_fallback()
        return {
            "summary": data.get("summary") or fallback["summary"],
            "historical_patterns": data.get("historical_patterns") or fallback["historical_patterns"],
            "assumptions_uncertainty": data.get("assumptions_uncertainty") or fallback["assumptions_uncertainty"],
            "business_implications": data.get("business_implications") or fallback["business_implications"],
            "recommendations": data.get("recommendations") or fallback["recommendations"],
            "model_used": fallback["model_used"],
            "trend_direction": fallback["trend_direction"],
            "projected_change_pct": fallback["projected_change_pct"],
            "confidence_level": fallback["confidence_level"],
            "ai_provider": model_name,
        }
    except Exception as e:
        logger.warning(f"Gemini forecast explanation failed: {e}")
        return _deterministic_fallback()

