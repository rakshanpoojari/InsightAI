import io
import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_insightai.db"

from app.main import app
from app.services.data_quality_detector import detect_data_quality_issues
from app.services.data_cleaning import apply_selected_quality_actions

client = TestClient(app)
with client:
    pass

MESSY_CSV = b"""Date,Product,Region,Units,Price,Revenue
2024-01-01,Widget A,North,10,$50.00,500
2024-01-02, widget a ,north,15,$50.00,750
2024-01-02, widget a ,north,15,$50.00,750
2024-01-03,Widget B,South,20,$100.00,2000
2024-01-04,Widget B,South,?,$100.00,
invalid-date,Widget C,East,5,$200.00,1000
2024-01-06,Widget C,East,10,$200.00,50
2024-01-07,Widget D,West,-5,$80.00,400
2024-01-08,Widget E,West,2,$99999.00,199998
"""


def test_detector_identifies_all_categories():
    df = pd.read_csv(io.BytesIO(MESSY_CSV))
    issues, score, cat_counts, sev_counts = detect_data_quality_issues(df, 1, "test")

    categories = {issue.category for issue in issues}
    # Should detect missing values, duplicates, text inconsistency, invalid dates, numeric formatting, invalid values, etc.
    assert "missing_values" in categories
    assert "duplicates" in categories
    assert "text_inconsistency" in categories
    assert "invalid_dates" in categories
    assert "numeric_formatting" in categories
    assert "invalid_values" in categories

    # Verify score computation
    assert 0 <= score <= 100


def test_quality_audit_endpoint():
    # Upload messy dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("messy_test.csv", io.BytesIO(MESSY_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # Call quality audit
    audit_res = client.get(f"/api/datasets/{dataset_id}/quality-audit")
    assert audit_res.status_code == 200
    data = audit_res.json()

    assert data["dataset_id"] == dataset_id
    assert data["total_rows"] == 9
    assert data["total_columns"] == 6
    assert len(data["issues"]) > 0
    assert "ai_summary" in data
    assert data["ai_summary"] is not None
    assert 0 <= data["quality_score"] <= 100
    assert "issues_count_by_category" in data
    assert "issues_count_by_severity" in data


def test_clean_preview_and_apply_flow():
    # Upload dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("clean_flow_test.csv", io.BytesIO(MESSY_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # Get audit
    audit = client.get(f"/api/datasets/{dataset_id}/quality-audit").json()
    issue_ids = [iss["id"] for iss in audit["issues"] if iss["category"] in ("duplicates", "text_inconsistency", "numeric_formatting")]
    assert len(issue_ids) > 0

    # 1. Preview clean
    preview_res = client.post(
        f"/api/datasets/{dataset_id}/clean/preview",
        json={"selected_issue_ids": issue_ids},
    )
    assert preview_res.status_code == 200
    preview_body = preview_res.json()
    assert preview_body["rows_before"] == 9
    assert preview_body["rows_after"] == 8  # 1 duplicate dropped
    assert preview_body["projected_quality_score"] >= preview_body["current_quality_score"]
    assert len(preview_body["sample_after_rows"]) > 0

    # 2. Apply clean
    apply_res = client.post(
        f"/api/datasets/{dataset_id}/clean/apply",
        json={"selected_issue_ids": issue_ids, "confirm": True},
    )
    assert apply_res.status_code == 200
    apply_body = apply_res.json()
    assert apply_body["rows_before"] == 9
    assert apply_body["rows_after"] == 8
    assert apply_body["new_quality_score"] >= apply_body["old_quality_score"]

    # Verify audit shows backup is available
    audit_after = client.get(f"/api/datasets/{dataset_id}/quality-audit").json()
    assert audit_after["has_backup"] is True
    assert audit_after["total_rows"] == 8

    # 3. Reset to original raw dataset
    reset_res = client.post(f"/api/datasets/{dataset_id}/clean/reset")
    assert reset_res.status_code == 200
    reset_body = reset_res.json()
    assert reset_body["row_count"] == 9

    # Verify audit recomputed back to original 9 rows
    audit_reset = client.get(f"/api/datasets/{dataset_id}/quality-audit").json()
    assert audit_reset["total_rows"] == 9


def test_export_clean_dataset_csv_and_xlsx():
    # Upload dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("export_test.csv", io.BytesIO(MESSY_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # Export CSV
    csv_res = client.get(f"/api/datasets/{dataset_id}/export?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert len(csv_res.content) > 0
    assert b"Widget A" in csv_res.content

    # Export Excel
    xlsx_res = client.get(f"/api/datasets/{dataset_id}/export?format=xlsx")
    assert xlsx_res.status_code == 200
    assert "spreadsheetml" in xlsx_res.headers["content-type"]
    assert len(xlsx_res.content) > 0
