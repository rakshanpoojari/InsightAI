from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas import AnomalyRequest, AnomalyResponse, ForecastRequest, ForecastResponse
from app.services import anomaly_detector, forecaster

logger = logging.getLogger("insightai.advanced")
router = APIRouter(prefix="/api/datasets/{dataset_id}", tags=["advanced"])


@router.post("/anomalies", response_model=AnomalyResponse)
def get_anomalies(dataset_id: int, request: AnomalyRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        raise HTTPException(status_code=400, detail="Dataset has no columns profiled.")

    try:
        return anomaly_detector.detect_anomalies(engine, dataset, columns, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to detect anomalies")
        raise HTTPException(status_code=500, detail=f"Failed to detect anomalies: {e}")


@router.post("/forecast", response_model=ForecastResponse)
def get_forecast(dataset_id: int, request: ForecastRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        raise HTTPException(status_code=400, detail="Dataset has no columns profiled.")

    try:
        return forecaster.run_forecast(engine, dataset, columns, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to run forecast")
        raise HTTPException(status_code=500, detail=f"Failed to run forecast: {e}")
