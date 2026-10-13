import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_insightai_platform.db"

from app.database import Base, engine
from app.main import app

Base.metadata.create_all(bind=engine)

client = TestClient(app)
with client:
    pass


def test_full_insightai_platform_suite():
    # 1. Load sample dataset
    r = client.post("/api/datasets/load-sample")
    assert r.status_code == 201, r.text
    ds = r.json()
    ds_id = ds["id"]
    assert ds["name"] == "sales_sample"
    assert ds["row_count"] > 0
    assert len(ds["columns"]) > 0

    # 2. Natural language query answering
    r = client.post(
        f"/api/datasets/{ds_id}/ask",
        json={"question": "What is the total sales by product?"},
    )
    assert r.status_code == 200, r.text
    nl_res = r.json()
    assert "sql" in nl_res
    assert len(nl_res["columns"]) >= 2
    assert len(nl_res["rows"]) > 0
    assert nl_res["chart_config"] is not None
    assert nl_res["summary"] is not None

    # 3. Raw SQL execution
    r = client.post(
        f"/api/datasets/{ds_id}/query",
        json={"sql": 'SELECT "Product", COUNT(*) as cnt FROM dataset GROUP BY "Product"'},
    )
    assert r.status_code == 200, r.text
    sql_res = r.json()
    assert len(sql_res["rows"]) > 0

    # 4. Prohibit unsafe SQL
    r = client.post(
        f"/api/datasets/{ds_id}/query",
        json={"sql": 'DROP TABLE dataset'},
    )
    assert r.status_code == 400

    # 5. Executive Dashboard
    r = client.get(f"/api/datasets/{ds_id}/dashboard")
    assert r.status_code == 200, r.text
    dash = r.json()
    assert len(dash["kpis"]) >= 3
    assert len(dash["charts"]) >= 1

    # 6. Statistical AI Insights
    r = client.get(f"/api/datasets/{ds_id}/insights")
    assert r.status_code == 200, r.text
    insights = r.json()
    assert len(insights["insights"]) >= 1
    assert "executive_summary" in insights

    # 7. Anomaly Detection
    r = client.post(
        f"/api/datasets/{ds_id}/anomalies",
        json={"target_column": "Sales", "contamination": 0.05},
    )
    assert r.status_code == 200, r.text
    anomalies = r.json()
    assert anomalies["total_rows"] > 0
    assert "chart_data" in anomalies

    # 8. Forecasting
    r = client.post(
        f"/api/datasets/{ds_id}/forecast",
        json={"target_column": "Sales", "date_column": "Date", "horizon": 7},
    )
    assert r.status_code == 200, r.text
    forecast = r.json()
    assert forecast["horizon"] == 7
    assert len(forecast["forecast_points"]) > 7
    assert "metrics" in forecast

    # 9. System Status & Diagnostics
    r = client.get("/api/system/status")
    assert r.status_code == 200, r.text
    sys_status = r.json()
    assert sys_status["status"] == "healthy"
    assert "sqlite" in sys_status
    assert "duckdb" in sys_status
    assert sys_status["duckdb"]["version"] != ""
    assert len(sys_status["sqlite"]["tables"]) > 0

    # 10. Dynamic AI Chat Suggestions
    r = client.get(f"/api/datasets/{ds_id}/suggestions")
    assert r.status_code == 200, r.text
    suggestions = r.json()
    assert isinstance(suggestions, list)
    assert len(suggestions) >= 4
    # Test executing the first generated dynamic suggestion
    top_suggestion = suggestions[0]
    r = client.post(f"/api/datasets/{ds_id}/ask", json={"question": top_suggestion})
    assert r.status_code == 200, f"Failed suggestion query '{top_suggestion}': {r.text}"
    sugg_res = r.json()
    assert "sql" in sugg_res
    assert len(sugg_res["rows"]) > 0

    # 11. CPI / Price Forecasting Options
    r = client.get(f"/api/datasets/{ds_id}/cpi/options")
    assert r.status_code == 200, r.text
    cpi_opts = r.json()
    assert cpi_opts["supported"] is True
    assert "price_column" in cpi_opts

    # 12. CPI / Price Forecast Execution (6-month horizon)
    r = client.post(
        f"/api/datasets/{ds_id}/cpi/forecast",
        json={"horizon_months": 6, "dimension_value": "All"},
    )
    assert r.status_code == 200, r.text
    cpi_fc = r.json()
    assert cpi_fc["horizon_months"] == 6
    assert cpi_fc["historical_observations"] > 0
    assert len(cpi_fc["points"]) > 6
    assert "purchasing_recommendation" in cpi_fc

    # 13. Official CPI Sample Dataset Loading & 12-Month Projection
    r = client.post("/api/datasets/load-cpi-sample")
    assert r.status_code == 201, r.text
    cpi_ds = r.json()
    cpi_ds_id = cpi_ds["id"]
    assert cpi_ds["name"] == "consumer_price_index_monthly"

    # Verify CPI capability detection on official CPI dataset
    r = client.get(f"/api/datasets/{cpi_ds_id}/cpi/options")
    assert r.status_code == 200
    official_opts = r.json()
    assert official_opts["mode"] == "cpi"
    assert "Food & Beverages" in str(official_opts["dimension_values"])

    # Forecast Food & Beverages for 12 months
    r = client.post(
        f"/api/datasets/{cpi_ds_id}/cpi/forecast",
        json={"horizon_months": 12, "dimension_column": "Category", "dimension_value": "Food & Beverages"},
    )
    assert r.status_code == 200, r.text
    food_cpi = r.json()
    assert food_cpi["horizon_months"] == 12
    assert food_cpi["current_index"] > 200
    assert len(food_cpi["points"]) > 12

    # Clean up test datasets
    client.delete(f"/api/datasets/{cpi_ds_id}")
    del_r = client.delete(f"/api/datasets/{ds_id}")
    assert del_r.status_code == 204
