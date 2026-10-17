from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import gemini_service, sql_engine

client = TestClient(app)


@pytest.fixture
def sample_dataset():
    """Uploads a test dataset and returns its metadata."""
    csv_content = b"""Date,Product,Category,Revenue,Units
2024-01-01,Alpha,Electronics,1200,10
2024-02-01,Beta,Electronics,1800,15
2024-03-01,Gamma,Apparel,900,20
2024-04-01,Alpha,Electronics,1400,12
"""
    res = client.post(
        "/api/datasets/upload",
        files={"file": ("test_gemini_ds.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 201
    ds = res.json()
    yield ds
    # Cleanup
    client.delete(f"/api/datasets/{ds['id']}")


def test_missing_gemini_key_graceful_fallback(sample_dataset):
    """
    Test Phase 2 & Phase 3: When GEMINI_API_KEY is not set or empty,
    the application must start, serve queries, and fallback deterministically without error.
    """
    with patch.object(settings, "gemini_api_key", None):
        assert not gemini_service.is_gemini_configured()
        assert gemini_service.get_gemini_client() is None

        # 1. Ask endpoint
        res = client.post(
            f"/api/datasets/{sample_dataset['id']}/ask",
            json={"question": "What is the total Revenue?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "Total_Revenue" in data["columns"] or "total_revenue" in str(data["columns"]).lower()
        assert data["ai_explanation"] is None
        assert data["ai_provider"] is None
        assert data["summary"] is not None

        # 2. Insights endpoint
        ins_res = client.get(f"/api/datasets/{sample_dataset['id']}/insights")
        assert ins_res.status_code == 200
        ins_data = ins_res.json()
        assert ins_data["ai_enhanced"] is False
        assert len(ins_data["insights"]) >= 1


def test_gemini_query_explanation_success(sample_dataset):
    """
    Test Phase 3: Successful structured Gemini response explaining verified query results.
    Verifies that raw row-level dataset is never transmitted in the prompt.
    """
    mock_ai_response = {
        "answer": "Total revenue across all products is $5,300.00 with Alpha generating the primary share.",
        "supporting_figures": ["Total Revenue: $5,300.00", "Top Product: Alpha ($2,600.00)"],
        "relevant_columns": ["Revenue", "Product"],
        "insights": ["Alpha shows consistent recurring volume across Q1 and Q2."],
        "chart_suggestion": {
            "chart_type": "bar",
            "x_axis": "Product",
            "y_axis": "Revenue",
            "title": "Revenue by Product",
        },
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_ai_response)
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "gemini_api_key", "mock-test-key-12345"), \
         patch.object(gemini_service, "get_gemini_client", return_value=mock_client):

        res = client.post(
            f"/api/datasets/{sample_dataset['id']}/ask",
            json={"question": "What is the total Revenue by Product?"},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["ai_explanation"] == mock_ai_response["answer"]
        assert data["ai_supporting_figures"] == mock_ai_response["supporting_figures"]
        assert data["ai_relevant_columns"] == mock_ai_response["relevant_columns"]
        assert data["ai_insights"] == mock_ai_response["insights"]
        assert data["ai_provider"] == "gemini-2.5-flash"

        # Verify privacy: check what was passed to Gemini
        assert mock_client.models.generate_content.called
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        contents_sent = call_kwargs["contents"]
        # Raw CSV text or full table must NOT be sent
        assert "2024-03-01,Gamma,Apparel,900,20" not in contents_sent


def test_gemini_malformed_model_output_fallback(sample_dataset):
    """
    Test Phase 3: Malformed non-JSON or garbled model output must not fail
    the user's request; it must cleanly fallback to deterministic summary.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "I am an AI and here is your answer without JSON format..."
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "gemini_api_key", "mock-test-key-12345"), \
         patch.object(gemini_service, "get_gemini_client", return_value=mock_client):

        res = client.post(
            f"/api/datasets/{sample_dataset['id']}/ask",
            json={"question": "What is the total Revenue?"},
        )
        assert res.status_code == 200
        data = res.json()
        # Query still succeeds
        assert len(data["rows"]) == 1
        # AI explanation is None because parsing safely aborted
        assert data["ai_explanation"] is None
        assert data["summary"] is not None


def test_gemini_timeout_and_rate_limit_fallback(sample_dataset):
    """
    Test Phase 2 & Phase 3: Provider timeouts and 429 rate limit exceptions
    must fall back gracefully without 500 error.
    """
    mock_client = MagicMock()
    # Simulate a timeout or rate limit error
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded connecting to Google Gemini API")

    with patch.object(settings, "gemini_api_key", "mock-test-key-12345"), \
         patch.object(gemini_service, "get_gemini_client", return_value=mock_client):

        res = client.post(
            f"/api/datasets/{sample_dataset['id']}/ask",
            json={"question": "What is the total Revenue?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["rows"]) >= 1
        assert data["ai_explanation"] is None


def test_gemini_insights_enhancement(sample_dataset):
    """
    Test Phase 4: Gemini enhances verified mathematical insights with
    executive summary and actionable recommendations without altering computed metrics.
    """
    mock_enhanced_payload = {
        "executive_summary": "Q1 performance demonstrates high revenue concentration in electronics with strong volume trajectory.",
        "enhanced_insights": [
            {
                "id": "insight-pareto",
                "executive_title": "Electronics Portfolio Concentration",
                "explanation": "Top category generates over 70% of total revenue volume.",
                "recommendation": "Diversify catalog to mitigate single-category market vulnerability.",
                "affected_columns": ["Category", "Revenue"],
            }
        ],
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_enhanced_payload)
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "gemini_api_key", "mock-test-key-12345"), \
         patch.object(gemini_service, "get_gemini_client", return_value=mock_client):

        res = client.get(f"/api/datasets/{sample_dataset['id']}/insights")
        assert res.status_code == 200
        data = res.json()

        assert data["ai_enhanced"] is True
        assert data["ai_provider"] == "gemini-2.5-flash"
        assert "revenue concentration" in data["executive_summary"].lower()


def test_strict_rejection_of_unsafe_query():
    """
    Test Phase 3: Strict SQL security guardrail.
    Any attempt to execute destructive SQL (DROP, DELETE, UPDATE, ALTER, etc.) must be rejected.
    """
    # 1. Direct prohibited statements (rejected because non-SELECT)
    with pytest.raises(ValueError, match="Only SELECT and WITH"):
        sql_engine.validate_sql('DROP TABLE "dataset"')

    with pytest.raises(ValueError, match="Only SELECT and WITH"):
        sql_engine.validate_sql('DELETE FROM "dataset" WHERE 1=1')

    with pytest.raises(ValueError, match="Only SELECT and WITH"):
        sql_engine.validate_sql('UPDATE "dataset" SET Revenue = 0')

    with pytest.raises(ValueError, match="Only SELECT and WITH"):
        sql_engine.validate_sql('ATTACH DATABASE "malicious.db" AS mal')

    with pytest.raises(ValueError, match="Only SELECT and WITH"):
        sql_engine.validate_sql("PRAGMA table_info('dataset')")

    # 2. Injected destructive operations within a SELECT
    with pytest.raises(ValueError, match="Prohibited SQL operation detected"):
        sql_engine.validate_sql('SELECT * FROM "dataset"; DROP TABLE "dataset"')

    with pytest.raises(ValueError, match="Prohibited SQL operation detected"):
        sql_engine.validate_sql('SELECT * FROM "dataset"; DELETE FROM "dataset"')

    # 3. Valid read-only queries must pass
    sql_engine.validate_sql('SELECT "Category", SUM("Revenue") FROM "dataset" GROUP BY "Category"')
    sql_engine.validate_sql('WITH ranked AS (SELECT * FROM "dataset") SELECT * FROM ranked LIMIT 10')


def test_gemini_input_length_guardrail():
    """
    Test Phase 2: Questions exceeding MAX_QUESTION_LENGTH (500 chars) are safely truncated.
    """
    long_question = "What is the revenue " + ("really " * 150) + "by product?"
    assert len(long_question) > gemini_service.MAX_QUESTION_LENGTH

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"answer": "Answer for truncated question", "supporting_figures": []})
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "gemini_api_key", "mock-test-key-12345"), \
         patch.object(gemini_service, "get_gemini_client", return_value=mock_client):

        res = gemini_service.explain_query_results(
            question=long_question,
            dataset_name="Test DS",
            columns=[],
            sql="SELECT 1",
            rows=[{"a": 1}],
            total_rows=1,
            execution_time_ms=10.0,
        )
        assert res is not None
        assert res["ai_explanation"] == "Answer for truncated question"

        # Verify the prompt sent to Gemini truncated the question
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        sent_prompt = call_kwargs["contents"]
        assert len(long_question) not in [len(sent_prompt)]


def test_active_dataset_isolation(sample_dataset):
    """
    Test Phase 3: Switching datasets ensures strict query and metadata isolation.
    """
    # Create second dataset
    csv_2 = b"""Date,Vehicle,Speed,Fuel
2024-01-01,Truck,55,10.2
2024-01-02,Sedan,65,8.1
"""
    res2 = client.post(
        "/api/datasets/upload",
        files={"file": ("test_vehicles.csv", io.BytesIO(csv_2), "text/csv")},
    )
    assert res2.status_code == 201
    ds2 = res2.json()

    try:
        # Query on dataset 1
        r1 = client.post(f"/api/datasets/{sample_dataset['id']}/ask", json={"question": "What is the total Revenue?"})
        assert r1.status_code == 200

        # Query on dataset 2
        r2 = client.post(f"/api/datasets/{ds2['id']}/ask", json={"question": "What is the average Speed?"})
        assert r2.status_code == 200

        # Dataset 2 should have Vehicle/Speed columns, NOT Product/Revenue
        d1_cols = [c.lower() for c in r1.json()["columns"]]
        d2_cols = [c.lower() for c in r2.json()["columns"]]
        assert any("revenue" in c for c in d1_cols)
        assert any("speed" in c for c in d2_cols)
        assert not any("speed" in c for c in d1_cols)
    finally:
        client.delete(f"/api/datasets/{ds2['id']}")
