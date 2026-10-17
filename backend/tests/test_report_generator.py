import io
import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_insightai.db"

from app.main import app
from app.database import engine
from app.models.dataset import Dataset, DatasetColumn
from app.services import report_generator

client = TestClient(app)
with client:
    pass

SAMPLE_CSV = b"""Date,Product,Region,Sales,Profit
2024-01-01,Widget A,North,1000,200
2024-01-02,Widget B,South,1500,300
2024-01-03,Widget A,North,1200,240
2024-01-04,Widget C,East,800,160
2024-01-05,Widget B,South,1600,320
2024-01-06,Widget C,East,900,180
2024-01-07,Widget A,North,1400,280
"""

MESSY_NO_DATE_CSV = b"""Item,Price,Quantity
Apples,5.5,10
Bananas,3.0,15
Oranges,4.0,12
Grapes,8.0,8
"""


def test_compile_report_data_and_pdf_generation():
    # 1. Upload dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("report_test.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # 2. Test compile_report_data
    with client:
        from app.database import SessionLocal
        db = SessionLocal()
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()

        report_data = report_generator.compile_report_data(
            engine=engine,
            dataset=dataset,
            columns=columns,
            target_column="Sales",
            date_column="Date",
            horizon=7,
        )
        db.close()

    assert report_data["total_rows"] == 7
    assert report_data["total_columns"] == 5
    assert report_data["primary_metric"] == "Sales"
    assert report_data["distribution"]["total"] == 8400.0
    assert "narrative" in report_data
    assert "executive_summary" in report_data["narrative"]

    # 3. Test generate_executive_pdf
    pdf_bytes = report_generator.generate_executive_pdf(report_data, title="Quarterly Executive Briefing")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_report_preview_endpoint():
    # Upload dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("preview_test.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    # Call preview endpoint
    payload = {
        "title": "InsightAI Performance Review",
        "subtitle": "Q1 Strategic Review",
        "target_column": "Sales",
        "date_column": "Date",
        "forecast_horizon": 10,
        "sections": {
            "executive_summary": True,
            "data_health_audit": True,
            "key_metrics_distribution": True,
            "ai_insights": True,
            "forecast_outlook": True,
            "strategic_action_plan": True,
        },
    }
    prev_res = client.post(f"/api/datasets/{dataset_id}/report/preview", json=payload)
    assert prev_res.status_code == 200
    prev_body = prev_res.json()

    assert prev_body["title"] == "InsightAI Performance Review"
    assert prev_body["dataset_id"] == dataset_id
    assert prev_body["total_rows"] == 7
    assert prev_body["distribution"]["total"] == 8400.0
    assert "narrative" in prev_body
    assert "executive_summary" in prev_body["narrative"]
    assert len(prev_body["narrative"]["action_plan"]) >= 2
    assert prev_body["forecast"] is not None
    assert prev_body["forecast"]["horizon"] == 10


def test_report_pdf_download_endpoint():
    # Upload dataset
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("pdf_dl_test.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    payload = {
        "title": "Corporate Executive PDF Briefing",
        "target_column": "Sales",
        "forecast_horizon": 7,
        "sections": {
            "executive_summary": True,
            "data_health_audit": False,
            "key_metrics_distribution": True,
            "ai_insights": True,
            "forecast_outlook": True,
            "strategic_action_plan": True,
        },
    }
    pdf_res = client.post(f"/api/datasets/{dataset_id}/report/pdf", json=payload)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_res.headers["content-disposition"]
    assert pdf_res.content.startswith(b"%PDF-")
    assert len(pdf_res.content) > 1000


def test_pdf_generation_robustness_without_date_column():
    # Test that PDF generation gracefully succeeds even on a dataset without temporal date columns
    r = client.post(
        "/api/datasets/upload",
        files={"file": ("no_date_test.csv", io.BytesIO(MESSY_NO_DATE_CSV), "text/csv")},
    )
    assert r.status_code == 201
    dataset_id = r.json()["id"]

    pdf_res = client.post(
        f"/api/datasets/{dataset_id}/report/pdf",
        json={"title": "Non-Temporal Portfolio Audit"},
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")
    assert len(pdf_res.content) > 1000
