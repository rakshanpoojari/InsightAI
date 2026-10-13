from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas import InsightsResponse
from app.services import insights_engine

logger = logging.getLogger("insightai.insights")
router = APIRouter(prefix="/api/datasets/{dataset_id}/insights", tags=["insights"])


@router.get("", response_model=InsightsResponse)
def get_insights(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        raise HTTPException(status_code=400, detail="Dataset has no columns profiled.")

    try:
        return insights_engine.generate_insights(engine, dataset, columns)
    except Exception as e:
        logger.exception("Failed to generate insights")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {e}")
