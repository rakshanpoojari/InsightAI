import io
import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_insightai.db"

from app.main import app
from app.services import gemini_service

client = TestClient(app)
with client:
    pass

TS_CSV = b"""Date,Revenue,Units
2024-01-01,1000,10
2024-01-02,1100,11
2024-01-03,1250,12
2024-01-04,1300,13
2024-01-05,1450,14
2024-01-06,1600,16
2024-01-07,1750,17
"""

CPI_CSV = b"""Date,Category,Price_Index
2023-01-01,Food,100.0
2023-02-01,Food,101.5
2023-03-01,Food,103.0
2023-04-01,Food,104.2
2023-05-01,Food,106.0
2023-06-01,Food,107.8
2023-07-01,Food,109.1
2023-08-01,Food,111.0
"""


def test_general_forecast_explainer():
    # 1. Upload time-series dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("ts_test.csv", io.BytesIO(TS_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # 2. Run forecast
    fc_res = client.post(
        f"/api/datasets/{dataset_id}/forecast",
        json={"target_column": "Revenue", "date_column": "Date", "horizon": 7},
    )
    assert fc_res.status_code == 200
    fc_body = fc_res.json()
    assert fc_body["horizon"] == 7
    assert "ai_explanation" in fc_body
    expl = fc_body["ai_explanation"]
    assert expl is not None

    # Verify structured fields
    assert "summary" in expl and len(expl["summary"]) > 10
    assert "historical_patterns" in expl
    assert "assumptions_uncertainty" in expl
    assert "business_implications" in expl
    assert "recommendations" in expl and len(expl["recommendations"]) >= 2
    assert expl["trend_direction"] in ("Upward", "Downward", "Stable")
    assert "model_used" in expl
    assert "confidence_level" in expl
    assert "ai_provider" in expl

    # 3. Call dedicated explain endpoint
    exp_res = client.post(
        f"/api/datasets/{dataset_id}/forecast/explain",
        json={"target_column": "Revenue", "date_column": "Date", "horizon": 7},
    )
    assert exp_res.status_code == 200
    exp_body = exp_res.json()
    assert exp_body["trend_direction"] == expl["trend_direction"]
    assert exp_body["projected_change_pct"] == expl["projected_change_pct"]


def test_cpi_forecast_explainer():
    # 1. Upload CPI dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("cpi_test.csv", io.BytesIO(CPI_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # 2. Run CPI forecast
    cpi_res = client.post(
        f"/api/datasets/{dataset_id}/cpi/forecast",
        json={
            "analysis_mode": "cpi",
            "date_column": "Date",
            "price_column": "Price_Index",
            "dimension_column": "Category",
            "dimension_value": "Food",
            "horizon_months": 6,
        },
    )
    assert cpi_res.status_code == 200
    cpi_body = cpi_res.json()
    assert "ai_explanation" in cpi_body
    expl = cpi_body["ai_explanation"]
    assert expl is not None

    # Verify structured fields
    assert "summary" in expl
    assert "historical_patterns" in expl
    assert "assumptions_uncertainty" in expl
    assert "business_implications" in expl
    assert len(expl["recommendations"]) >= 2
    assert "annualized rate" in expl["summary"].lower() or "cpi" in expl["summary"].lower()

    # 3. Call dedicated CPI explain endpoint
    exp_res = client.post(
        f"/api/datasets/{dataset_id}/cpi/forecast/explain",
        json={
            "analysis_mode": "cpi",
            "date_column": "Date",
            "price_column": "Price_Index",
            "dimension_column": "Category",
            "dimension_value": "Food",
            "horizon_months": 6,
        },
    )
    assert exp_res.status_code == 200
    exp_body = exp_res.json()
    assert exp_body["projected_change_pct"] == expl["projected_change_pct"]


def test_direct_forecast_explainer_fallbacks():
    # Test fallback directly without Gemini API
    general_metrics = {
        "dataset_name": "Sales",
        "target_column": "Revenue",
        "date_column": "Date",
        "horizon": 14,
        "trend_direction": "Upward",
        "slope": 25.5,
        "r_squared": 0.88,
        "expected_growth_pct": 12.4,
        "avg_historical": 1000.0,
        "projected_horizon_avg": 1124.0,
        "historical_points_count": 30,
    }
    res_gen = gemini_service.explain_forecast(general_metrics, is_cpi=False)
    assert "12.4%" in res_gen["summary"]
    assert len(res_gen["recommendations"]) >= 2
    assert res_gen["trend_direction"] == "Upward"

    cpi_metrics = {
        "dataset_name": "Inflation",
        "mode_label": "Consumer Price Index (CPI)",
        "selected_dimension_value": "All Items",
        "horizon_months": 6,
        "current_index": 120.0,
        "projected_change_pct": 3.2,
        "annualized_rate_pct": 6.5,
        "volatility_pct": 2.1,
        "model_name": "Holt's Exponential Smoothing",
        "fit_mape": 0.95,
        "purchasing_recommendation": "Advance purchase required.",
    }
    res_cpi = gemini_service.explain_forecast(cpi_metrics, is_cpi=True)
    assert "3.2%" in res_cpi["summary"]
    assert "6.5%" in res_cpi["summary"]
    assert len(res_cpi["recommendations"]) >= 2
