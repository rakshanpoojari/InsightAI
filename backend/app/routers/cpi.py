from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.services import cpi_engine, data_profiling, storage

logger = logging.getLogger("insightai.cpi")
router = APIRouter(prefix="/api/datasets", tags=["cpi"])


class CpiForecastRequest(BaseModel):
    analysis_mode: Optional[str] = "auto"
    date_column: Optional[str] = None
    price_column: Optional[str] = None
    dimension_column: Optional[str] = None
    dimension_value: Optional[str] = "All"
    horizon_months: int = Field(default=6, ge=1, le=24)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/{dataset_id}/cpi/options")
def get_cpi_options(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    try:
        return cpi_engine.detect_cpi_capabilities(engine, dataset, columns)
    except Exception as e:
        logger.exception("Failed to detect CPI capabilities")
        raise HTTPException(status_code=500, detail=f"Failed to detect CPI capabilities: {e}")


@router.get("/{dataset_id}/cpi/series")
def get_cpi_historical_series(
    dataset_id: int,
    date_column: Optional[str] = None,
    price_column: Optional[str] = None,
    dimension_column: Optional[str] = None,
    dimension_value: Optional[str] = "All",
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    try:
        return cpi_engine.get_historical_series(
            engine=engine,
            dataset=dataset,
            columns=columns,
            date_column=date_column,
            price_column=price_column,
            dimension_column=dimension_column,
            dimension_value=dimension_value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to retrieve CPI series")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve CPI series: {e}")


@router.post("/{dataset_id}/cpi/forecast")
def get_cpi_forecast(
    dataset_id: int,
    request: CpiForecastRequest,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    try:
        return cpi_engine.run_cpi_forecast(
            engine=engine,
            dataset=dataset,
            columns=columns,
            analysis_mode=request.analysis_mode,
            date_column=request.date_column,
            price_column=request.price_column,
            dimension_column=request.dimension_column,
            dimension_value=request.dimension_value,
            horizon_months=request.horizon_months,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to run CPI forecasting")
        raise HTTPException(status_code=500, detail=f"Failed to run CPI forecasting: {e}")


@router.post("/load-cpi-sample", status_code=status.HTTP_201_CREATED)
def load_cpi_sample_dataset(db: Session = Depends(get_db)):
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "sample_data",
        "cpi_sample.csv",
    )
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="CPI sample dataset file not found.")

    with open(sample_path, "rb") as f:
        contents = f.read()

    ext = "csv"
    dataset_name = "consumer_price_index_monthly"
    table_name = storage.make_storage_table_name(dataset_name)

    df = storage.read_upload_to_dataframe(contents, ext)

    dataset = Dataset(
        name=dataset_name,
        original_filename="cpi_sample.csv",
        file_type=ext,
        storage_table_name=table_name,
        status="uploaded",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    storage.persist_dataframe(engine, table_name, df)
    profiles = data_profiling.profile_dataframe(df)

    db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset.id).delete()
    for p in profiles:
        db.add(DatasetColumn(dataset_id=dataset.id, **p))
    dataset.row_count = len(df)
    dataset.column_count = df.shape[1]
    dataset.quality_score = data_profiling.compute_quality_score(df, profiles)
    dataset.status = "profiled"
    db.commit()
    db.refresh(dataset)

    return dataset
