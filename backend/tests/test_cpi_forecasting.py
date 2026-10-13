import io
import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_insightai_cpi.db"

from app.database import Base, engine
from app.main import app

Base.metadata.create_all(bind=engine)
client = TestClient(app)
with client:
    pass


def upload_test_csv(csv_bytes: bytes, filename: str = "test.csv") -> int:
    r = client.post(
        "/api/datasets/upload",
        files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_authentic_cpi_dataset_and_horizons():
    # 1. Load authentic BLS CPI sample
    r = client.post("/api/datasets/load-cpi-sample")
    assert r.status_code == 201, r.text
    ds_id = r.json()["id"]

    # Check capabilities
    r = client.get(f"/api/datasets/{ds_id}/cpi/options")
    assert r.status_code == 200
    opts = r.json()
    assert opts["supported"] is True
    assert opts["mode"] == "cpi"
    assert "Consumer Price Index (CPI)" in opts["mode_label"]
    assert "Category" in opts["dimension_columns"]
    assert len(opts["available_price_columns"]) >= 2

    # Test 3-month, 6-month, and 12-month horizons
    for h in [3, 6, 12]:
        rf = client.post(
            f"/api/datasets/{ds_id}/cpi/forecast",
            json={"horizon_months": h, "dimension_value": "All"},
        )
        assert rf.status_code == 200, rf.text
        data = rf.json()
        assert data["horizon_months"] == h
        assert data["historical_observations"] >= 12
        assert data["current_index"] > 200.0
        assert data["forecasted_index"] > 200.0
        assert "forecast_start_date" in data
        assert "forecast_end_date" in data

        # Mathematical verification: expected_change_pct
        calc_pct = round(((data["forecasted_index"] - data["current_index"]) / data["current_index"]) * 100.0, 2)
        assert data["expected_change_pct"] == calc_pct

        # Mathematical verification: compounded annualized rate
        ratio = data["forecasted_index"] / data["current_index"]
        calc_annualized = round(((ratio ** (12.0 / h)) - 1.0) * 100.0, 2)
        assert data["annualized_rate_pct"] == calc_annualized

        # Chart points verification
        pts = data["points"]
        forecast_pts = [p for p in pts if p["is_forecast"]]
        assert len(forecast_pts) == h

        # Bridge point verification: anchor point has actual == predicted
        anchor_pts = [p for p in pts if p.get("is_anchor")]
        assert len(anchor_pts) == 1
        assert anchor_pts[0]["actual"] == anchor_pts[0]["predicted"]
        assert anchor_pts[0]["actual"] == data["current_index"]

        # Verify confidence intervals widen over horizon
        ci_widths = [p["upper_bound"] - p["lower_bound"] for p in forecast_pts]
        assert ci_widths[-1] >= ci_widths[0]

    # Test series endpoint
    rs = client.get(f"/api/datasets/{ds_id}/cpi/series")
    assert rs.status_code == 200
    s_data = rs.json()
    assert len(s_data["series"]) >= 12

    client.delete(f"/api/datasets/{ds_id}")


def test_product_price_and_price_index_modes():
    # Dataset with Product, Category, Date, Unit_Price
    csv_data = b"""Date,Product,Category,Unit_Price
2023-01-15,Widget X,Gadgets,50.0
2023-02-15,Widget X,Gadgets,52.0
2023-03-15,Widget X,Gadgets,54.5
2023-04-15,Widget X,Gadgets,55.0
2023-05-15,Widget X,Gadgets,57.2
2023-06-15,Widget X,Gadgets,59.0
2023-07-15,Widget X,Gadgets,61.0
"""
    ds_id = upload_test_csv(csv_data, "product_prices.csv")

    opts = client.get(f"/api/datasets/{ds_id}/cpi/options").json()
    assert opts["supported"] is True
    assert opts["mode"] == "product_price"
    assert "Product" in opts["dimension_columns"]

    # 1. Product Price Forecast (nominal currency)
    rf1 = client.post(
        f"/api/datasets/{ds_id}/cpi/forecast",
        json={"analysis_mode": "product_price", "horizon_months": 6},
    )
    assert rf1.status_code == 200
    d1 = rf1.json()
    assert d1["mode"] == "product_price"
    assert d1["unit_label"] == "Nominal Price ($)"
    assert d1["current_index"] == 61.0
    assert d1["forecasted_index"] > 61.0

    # 2. Price Index Estimate (Base = 100)
    rf2 = client.post(
        f"/api/datasets/{ds_id}/cpi/forecast",
        json={"analysis_mode": "price_index", "horizon_months": 6},
    )
    assert rf2.status_code == 200
    d2 = rf2.json()
    assert d2["mode"] == "price_index"
    assert "Base Period = 100" in d2["mode_label"]
    # Base 50.0 -> 100.0, current 61.0 -> 122.0
    assert round(d2["current_index"], 1) == 122.0

    client.delete(f"/api/datasets/{ds_id}")


def test_missing_interior_months_gap_handling():
    # January, March, May (February and April are missing gaps)
    csv_data = b"""Date,Category,Price
2023-01-01,Supplies,100.0
2023-03-01,Supplies,120.0
2023-05-01,Supplies,140.0
"""
    ds_id = upload_test_csv(csv_data, "gap_data.csv")

    rf = client.post(
        f"/api/datasets/{ds_id}/cpi/forecast",
        json={"horizon_months": 3},
    )
    assert rf.status_code == 200, rf.text
    d = rf.json()
    # Missing months should be interpolated: Jan(100), Feb(110), Mar(120), Apr(130), May(140) = 5 periods
    assert d["historical_observations"] == 5
    assert d["current_index"] == 140.0

    client.delete(f"/api/datasets/{ds_id}")


def test_invalid_dates_and_non_numeric_handling():
    csv_data = b"""Date,Item,Cost
2023-01-01,Hardware,200.0
NOT_A_DATE,Hardware,210.0
2023-02-01,Hardware,CORRUPT_VALUE
2023-02-01,Hardware,205.0
2023-03-01,Hardware,210.0
2023-04-01,Hardware,215.0
"""
    ds_id = upload_test_csv(csv_data, "dirty_data.csv")
    rf = client.post(f"/api/datasets/{ds_id}/cpi/forecast", json={"horizon_months": 3})
    assert rf.status_code == 200
    d = rf.json()
    assert d["historical_observations"] >= 3
    client.delete(f"/api/datasets/{ds_id}")


def test_insufficient_historical_observations():
    # Only 2 monthly points -> should return HTTP 400
    csv_data = b"""Date,Item,Price
2023-01-01,Alpha,10.0
2023-02-01,Alpha,12.0
"""
    ds_id = upload_test_csv(csv_data, "short_data.csv")
    rf = client.post(f"/api/datasets/{ds_id}/cpi/forecast", json={"horizon_months": 3})
    assert rf.status_code == 400
    assert "Insufficient" in rf.json()["detail"]
    client.delete(f"/api/datasets/{ds_id}")


def test_dataset_without_price_column():
    csv_data = b"""Date,Employee,Department
2023-01-01,Alice,Engineering
2023-02-01,Bob,Marketing
2023-03-01,Charlie,Sales
"""
    ds_id = upload_test_csv(csv_data, "no_price.csv")
    opts = client.get(f"/api/datasets/{ds_id}/cpi/options").json()
    assert opts["supported"] is False
    assert "lacks suitable" in opts["reason"]

    rf = client.post(f"/api/datasets/{ds_id}/cpi/forecast", json={"horizon_months": 3})
    assert rf.status_code == 400
    client.delete(f"/api/datasets/{ds_id}")


def test_constant_series_forecasting():
    # Exactly constant series: 40.0 every month
    csv_data = b"""Date,Item,Price
2023-01-01,Standard,40.0
2023-02-01,Standard,40.0
2023-03-01,Standard,40.0
2023-04-01,Standard,40.0
2023-05-01,Standard,40.0
"""
    ds_id = upload_test_csv(csv_data, "constant_data.csv")
    rf = client.post(f"/api/datasets/{ds_id}/cpi/forecast", json={"horizon_months": 6})
    assert rf.status_code == 200
    d = rf.json()
    assert d["is_constant_series"] is True
    assert d["current_index"] == 40.0
    assert d["forecasted_index"] == 40.0
    assert d["expected_change_pct"] == 0.0
    assert d["annualized_rate_pct"] == 0.0
    assert d["volatility_pct"] == 0.0
    for p in d["points"]:
        if p["is_forecast"]:
            assert p["predicted"] == 40.0
            assert p["lower_bound"] == 40.0
            assert p["upper_bound"] == 40.0
    client.delete(f"/api/datasets/{ds_id}")