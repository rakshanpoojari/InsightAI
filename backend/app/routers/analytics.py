from __future__ import annotations

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas import AskQuestionRequest, QueryResult, RawQueryRequest
from app.services import gemini_service, nl_query, sql_engine, suggestions_engine

logger = logging.getLogger("insightai.analytics")
router = APIRouter(prefix="/api/datasets/{dataset_id}", tags=["analytics"])


@router.post("/query", response_model=QueryResult)
def run_sql_query(dataset_id: int, request: RawQueryRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        result = sql_engine.execute_query(engine, dataset.storage_table_name, request.sql)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("SQL execution failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.post("/ask", response_model=QueryResult)
def ask_question(dataset_id: int, request: AskQuestionRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        raise HTTPException(status_code=400, detail="Dataset has no columns profiled.")

    try:
        sql, summary = nl_query.translate_question_to_sql(request.question, dataset, columns)
        result = sql_engine.execute_query(engine, dataset.storage_table_name, sql)
        result.summary = summary

        # Enrich with Gemini AI explanation if configured
        if gemini_service.is_gemini_configured():
            ai_data = gemini_service.explain_query_results(
                question=request.question,
                dataset_name=dataset.name,
                columns=columns,
                sql=result.sql,
                rows=result.rows,
                total_rows=result.total_rows,
                execution_time_ms=result.execution_time_ms,
            )
            if ai_data:
                result.ai_explanation = ai_data.get("ai_explanation")
                result.ai_supporting_figures = ai_data.get("ai_supporting_figures")
                result.ai_relevant_columns = ai_data.get("ai_relevant_columns")
                result.ai_insights = ai_data.get("ai_insights")
                result.ai_provider = ai_data.get("ai_provider")

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Natural language querying failed")
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {e}")


@router.get("/suggestions", response_model=List[str])
def get_dataset_suggestions(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        return ["What is the total number of records?"]

    return suggestions_engine.generate_dynamic_suggestions(columns, dataset.name)
