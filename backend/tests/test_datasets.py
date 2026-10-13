import io
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_insightai.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import engine

# Using TestClient as a context manager ensures FastAPI's startup event
# (which creates DB tables) actually runs before requests are made.
client = TestClient(app)
with client:
    pass

CSV_CONTENT = b"""Date,Product,Region,Sales,Profit
2024-01-01,Widget A,North,1000,200
2024-01-02,Widget B,South,1500,
2024-01-02,Widget B,South,1500,300
2024-01-02,Widget B,South,1500,300
2024-01-04,Widget C,East,900,180
"""


def test_health_check():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_rejects_bad_extension():
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 400


def test_upload_rejects_empty_file():
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("data.csv", io.BytesIO(b""), "text/csv")},
    )
    assert r.status_code == 400


def test_upload_profile_preview_clean_flow():
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("sales.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["row_count"] == 5
    assert body["column_count"] == 5
    assert body["status"] == "profiled"
    assert 0 <= body["quality_score"] <= 100
    col_names = {c["name"] for c in body["columns"]}
    assert col_names == {"Date", "Product", "Region", "Sales", "Profit"}

    dataset_id = body["id"]

    # Preview
    r = client.get(f"/api/datasets/{dataset_id}/preview")
    assert r.status_code == 200
    preview = r.json()
    assert preview["total_rows"] == 5
    assert len(preview["rows"]) == 5

    # Clean
    r = client.post(
        f"/api/datasets/{dataset_id}/clean",
        json={
            "drop_duplicate_rows": True,
            "fill_missing_numeric": "median",
            "fill_missing_categorical": "mode",
            "trim_whitespace": True,
        },
    )
    assert r.status_code == 200
    cleaned = r.json()
    # One exact duplicate row should have been dropped
    assert cleaned["row_count"] == 4
    assert cleaned["status"] == "cleaned"

    # List
    r = client.get("/api/datasets")
    assert r.status_code == 200
    assert any(d["id"] == dataset_id for d in r.json())

    # Delete
    r = client.delete(f"/api/datasets/{dataset_id}")
    assert r.status_code == 204

    r = client.get(f"/api/datasets/{dataset_id}")
    assert r.status_code == 404


def teardown_module(module):
    pass
