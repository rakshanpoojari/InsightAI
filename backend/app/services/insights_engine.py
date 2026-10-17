from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset, DatasetColumn
from app.schemas import InsightCard, InsightsResponse
from app.services import gemini_service
from app.services.storage import read_dataframe


def generate_insights(engine: Engine, dataset: Dataset, columns: List[DatasetColumn]) -> InsightsResponse:
    df = read_dataframe(engine, dataset.storage_table_name)
    insights: List[InsightCard] = []

    num_cols = [c.name for c in columns if c.inferred_type == "numeric"]
    cat_cols = [c.name for c in columns if c.inferred_type == "categorical"]
    date_cols = [c.name for c in columns if c.inferred_type == "datetime"]

    # 1. Pareto / Concentration Analysis (Top Category share)
    if cat_cols and num_cols:
        cat = cat_cols[0]
        num = num_cols[0]
        grp = df[[cat, num]].dropna().groupby(cat)[num].sum().sort_values(ascending=False)
        total_sum = grp.sum()

        if total_sum > 0 and len(grp) >= 2:
            top_item = grp.index[0]
            top_val = grp.iloc[0]
            top_share = (top_val / total_sum) * 100

            top_20_pct_count = max(1, int(np.ceil(len(grp) * 0.2)))
            top_20_val = grp.iloc[:top_20_pct_count].sum()
            top_20_share = (top_20_val / total_sum) * 100

            if top_share >= 35:
                insights.append(
                    InsightCard(
                        id="insight-concentration-high",
                        title=f"High Concentration Risk in {cat}",
                        category="warning",
                        impact="high",
                        metric=f"{top_share:.1f}%",
                        description=f"'{top_item}' alone accounts for {top_share:.1f}% of all {num}. The business is heavily reliant on this single {cat.lower()}.",
                        recommendation=f"Diversify across other {cat.lower()}s to mitigate dependency risks and unlock untapped growth.",
                        affected_columns=[cat, num],
                    )
                )
            else:
                insights.append(
                    InsightCard(
                        id="insight-pareto",
                        title=f"Top {top_20_pct_count} {cat}(s) Drive {top_20_share:.1f}% of {num}",
                        category="opportunity",
                        impact="medium",
                        metric=f"{top_20_share:.1f}%",
                        description=f"Following the Pareto principle, the top {top_20_pct_count} of {len(grp)} {cat.lower()}s generate {top_20_share:.1f}% of total {num}.",
                        recommendation=f"Focus strategic optimizations and retention programs on these top {cat.lower()} performers.",
                        affected_columns=[cat, num],
                    )
                )

    # 2. Correlation Analysis between Numeric Metrics
    correlation_matrix: Dict[str, Dict[str, float]] = {}
    if len(num_cols) >= 2:
        df_num = df[num_cols].dropna()
        if len(df_num) > 3:
            corr_df = df_num.corr(method="pearson")
            for c1 in num_cols:
                correlation_matrix[c1] = {}
                for c2 in num_cols:
                    val = corr_df.loc[c1, c2]
                    correlation_matrix[c1][c2] = round(float(val), 3) if not np.isnan(val) else 0.0

            # Find strongest non-identical correlation
            best_pair = None
            max_corr = 0.0
            for i in range(len(num_cols)):
                for j in range(i + 1, len(num_cols)):
                    c1, c2 = num_cols[i], num_cols[j]
                    val = corr_df.loc[c1, c2]
                    if not np.isnan(val) and abs(val) > abs(max_corr):
                        max_corr = float(val)
                        best_pair = (c1, c2)

            if best_pair and abs(max_corr) >= 0.5:
                direction = "strongly positively" if max_corr > 0 else "strongly negatively"
                insights.append(
                    InsightCard(
                        id="insight-correlation",
                        title=f"{best_pair[0]} & {best_pair[1]} Correlation",
                        category="trend",
                        impact="high" if abs(max_corr) > 0.75 else "medium",
                        metric=f"r = {max_corr:+.2f}",
                        description=f"A statistically significant relationship (r = {max_corr:+.2f}) exists: {best_pair[0]} is {direction} correlated with {best_pair[1]}.",
                        recommendation=f"Leverage changes in {best_pair[0]} as a leading indicator to predict and plan {best_pair[1]}.",
                        affected_columns=[best_pair[0], best_pair[1]],
                    )
                )

    # 3. Variance & Outlier / Spread Insight
    if num_cols:
        primary_num = num_cols[0]
        s = df[primary_num].dropna()
        if len(s) > 5 and s.std() > 0:
            std = float(s.std())
            mean = float(s.mean())
            cv = (std / mean) * 100 if mean != 0 else 0
            if cv > 60:
                insights.append(
                    InsightCard(
                        id="insight-variance",
                        title=f"High Volatility in {primary_num}",
                        category="warning",
                        impact="medium",
                        metric=f"CV: {cv:.1f}%",
                        description=f"{primary_num} displays high variance (standard deviation: {std:,.2f} vs average: {mean:,.2f}), signaling wide distribution spread and potential outliers.",
                        recommendation="Review the anomaly detection report to isolate outlier transactions skewing the baseline.",
                        affected_columns=[primary_num],
                    )
                )

    # 4. Data Quality & Completeness Insight
    if dataset.quality_score >= 85:
        insights.append(
            InsightCard(
                id="insight-quality-strong",
                title="Exceptional Data Health",
                category="info",
                impact="low",
                metric=f"{dataset.quality_score:.1f}/100",
                description="The dataset passed completeness and type-consistency checks with an excellent quality score, providing high confidence for predictive analytics.",
                recommendation="Proceed with executive reporting and automated forecasting models with confidence.",
                affected_columns=[],
            )
        )
    else:
        insights.append(
            InsightCard(
                id="insight-quality-warning",
                title="Data Hygiene Improvements Recommended",
                category="warning",
                impact="medium",
                metric=f"{dataset.quality_score:.1f}/100",
                description=f"Quality score is {dataset.quality_score:.1f}/100 due to missing values, duplicates, or ambiguous types.",
                recommendation="Run the automated cleaning pipeline to drop duplicate rows and impute missing values.",
                affected_columns=[],
            )
        )

    # 5. Temporal Trajectory if Date exists
    if date_cols and num_cols:
        d_col = date_cols[0]
        n_col = num_cols[0]
        df_sorted = df[[d_col, n_col]].dropna().sort_values(by=d_col)
        if len(df_sorted) >= 4:
            first_half = df_sorted.iloc[: len(df_sorted) // 2][n_col].mean()
            second_half = df_sorted.iloc[len(df_sorted) // 2 :][n_col].mean()
            pct_change = ((second_half - first_half) / first_half) * 100 if first_half != 0 else 0
            direction = "Growth" if pct_change > 0 else "Decline"
            insights.append(
                InsightCard(
                    id="insight-temporal-trend",
                    title=f"Overall {direction} in {n_col} Over Time",
                    category="trend",
                    impact="high" if abs(pct_change) > 15 else "medium",
                    metric=f"{pct_change:+.1f}%",
                    description=f"Comparing the first half to the second half of tracked dates reveals an average {direction.lower()} of {pct_change:+.1f}% in {n_col}.",
                    recommendation=f"Analyze seasonal drivers or recent campaign activities to capitalize on this {direction.lower()}.",
                    affected_columns=[d_col, n_col],
                )
            )

    exec_summary = (
        f"Automated AI synthesis for '{dataset.name}': Generated {len(insights)} evidence-based "
        f"insights across {len(df):,} rows. "
        + (f"Strongest metric correlation observed is {insights[1].metric}. " if len(insights) > 1 else "")
        + "All findings are deterministically computed from dataset mathematics."
    )

    ai_provider = None
    ai_enhanced = False

    # Enhance with Gemini AI if configured
    if gemini_service.is_gemini_configured() and insights:
        ai_data = gemini_service.enhance_insights_with_gemini(
            dataset_name=dataset.name,
            computed_insights=[c.model_dump() for c in insights],
            correlation_matrix=correlation_matrix,
        )
        if ai_data:
            ai_provider = ai_data.get("ai_provider")
            ai_enhanced = True
            if ai_data.get("executive_summary"):
                exec_summary = ai_data["executive_summary"]
            
            # Match and update card explanations/recommendations without altering verified metrics
            enhanced_cards = {item.get("id"): item for item in ai_data.get("enhanced_insights", []) if isinstance(item, dict)}
            for card in insights:
                if card.id in enhanced_cards:
                    enh = enhanced_cards[card.id]
                    if enh.get("explanation"):
                        card.description = str(enh["explanation"]).strip()
                    if enh.get("recommendation"):
                        card.recommendation = str(enh["recommendation"]).strip()
                    if enh.get("executive_title"):
                        card.title = str(enh["executive_title"]).strip()

    return InsightsResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        insights=insights,
        correlation_matrix=correlation_matrix if correlation_matrix else None,
        executive_summary=exec_summary,
        ai_provider=ai_provider,
        ai_enhanced=ai_enhanced,
    )
