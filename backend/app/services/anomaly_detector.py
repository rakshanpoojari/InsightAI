from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.engine import Engine

from app.models.dataset import Dataset, DatasetColumn
from app.schemas import AnomalyPoint, AnomalyRequest, AnomalyResponse
from app.services.storage import read_dataframe


def detect_anomalies(
    engine: Engine,
    dataset: Dataset,
    columns: List[DatasetColumn],
    request: AnomalyRequest,
) -> AnomalyResponse:
    df = read_dataframe(engine, dataset.storage_table_name)
    if df.empty:
        raise ValueError("Dataset is empty.")

    num_cols = [c.name for c in columns if c.inferred_type == "numeric"]
    if not num_cols:
        raise ValueError("Anomaly detection requires at least one numeric column.")

    target_col = request.target_column or num_cols[0]
    if target_col not in df.columns:
        target_col = num_cols[0]

    coerced = pd.to_numeric(
        df[target_col].astype(str).str.replace(",", "").str.strip(),
        errors="coerce",
    )
    med = float(coerced.median()) if not coerced.dropna().empty else 0.0
    if np.isnan(med):
        med = 0.0
    series = coerced.fillna(med)

    # 1. Statistical Z-Score
    mean = series.mean()
    std = series.std() if series.std() > 0 else 1.0
    z_scores = np.abs((series - mean) / std)

    # 2. IQR bounds
    q25 = series.quantile(0.25)
    q75 = series.quantile(0.75)
    iqr = q75 - q25
    lower_iqr = q25 - 1.5 * iqr
    upper_iqr = q75 + 1.5 * iqr

    # 3. Isolation Forest for multi-signal anomaly confirmation
    contamination = max(0.01, min(request.contamination, 0.20))
    X = series.values.reshape(-1, 1)
    iso = IsolationForest(contamination=contamination, random_state=42)
    iso_preds = iso.fit_predict(X)  # -1 for anomaly, 1 for normal
    iso_scores = iso.score_samples(X)  # lower = more abnormal

    anomaly_points: List[AnomalyPoint] = []
    chart_data: List[Dict[str, Any]] = []

    # Find identifying column (date or category or row index)
    id_col = None
    for c in columns:
        if c.inferred_type in ("datetime", "categorical") and c.name != target_col:
            id_col = c.name
            break

    for idx, (val, z, iso_p, iso_s) in enumerate(zip(series, z_scores, iso_preds, iso_scores)):
        is_stat_anomaly = z > 2.5 or val < lower_iqr or val > upper_iqr
        is_iso_anomaly = iso_p == -1
        is_anomaly = bool(is_stat_anomaly or is_iso_anomaly)

        reasons = []
        if z > 2.5:
            reasons.append(f"Z-Score {z:.2f} > 2.5σ threshold (value {val:,.2f} vs avg {mean:,.2f})")
        if val > upper_iqr:
            reasons.append(f"Exceeds upper IQR boundary of {upper_iqr:,.2f}")
        elif val < lower_iqr:
            reasons.append(f"Falls below lower IQR boundary of {lower_iqr:,.2f}")
        if is_iso_anomaly and not reasons:
            reasons.append("Flagged by IsolationForest multidimensional density estimator")

        label = str(df.iloc[idx][id_col]) if id_col else f"Row {idx + 1}"
        chart_data.append(
            {
                "index": idx + 1,
                "label": label,
                target_col: round(float(val), 2),
                "is_anomaly": is_anomaly,
                "anomaly_score": round(float(1 - ((iso_s - iso_scores.min()) / (iso_scores.max() - iso_scores.min() + 1e-6))), 3),
            }
        )

        if is_anomaly:
            row_dict = {str(k): (round(float(v), 2) if isinstance(v, (int, float, np.number)) else str(v)) for k, v in df.iloc[idx].to_dict().items()}
            anomaly_points.append(
                AnomalyPoint(
                    index=idx + 1,
                    is_anomaly=True,
                    score=round(float(z), 2),
                    row=row_dict,
                    reasons=reasons,
                )
            )

    # Sort anomalies by highest z-score
    anomaly_points.sort(key=lambda x: x.score, reverse=True)
    anomaly_count = len(anomaly_points)
    anomaly_pct = round((anomaly_count / len(df)) * 100, 2)

    summary = (
        f"Detected {anomaly_count} anomalous data point(s) ({anomaly_pct}% of total records) "
        f"in target metric '{target_col}'. "
        + (f"Most severe deviation observed: {anomaly_points[0].reasons[0]}." if anomaly_points else "No critical anomalies detected.")
    )

    return AnomalyResponse(
        dataset_id=dataset.id,
        target_column=target_col,
        total_rows=len(df),
        anomaly_count=anomaly_count,
        anomaly_pct=anomaly_pct,
        chart_data=chart_data[:100],  # send up to 100 points for smooth visualization
        anomalies=anomaly_points[:50],
        summary=summary,
    )
