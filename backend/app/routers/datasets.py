from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas import CleaningOptions, DatasetDetail, DatasetPreview, DatasetSummary
from app.services import data_cleaning, data_profiling, storage

logger = logging.getLogger("insightai.datasets")
router = APIRouter(prefix="/api/datasets", tags=["datasets"])

MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


def _save_profile(db: Session, dataset: Dataset, df, profiles: list[dict]) -> None:
    # Replace existing column rows for this dataset (e.g. on re-clean)
    db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset.id).delete()
    for p in profiles:
        db.add(DatasetColumn(dataset_id=dataset.id, **p))
    dataset.row_count = len(df)
    dataset.column_count = df.shape[1]
    dataset.quality_score = data_profiling.compute_quality_score(df, profiles)
    db.commit()


@router.post("/upload", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No filename provided.")

    try:
        ext = storage.get_extension(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {settings.max_upload_mb} MB.",
        )

    try:
        df = storage.read_upload_to_dataframe(contents, ext)
    except Exception as e:
        logger.exception("Failed to parse upload")
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    dataset_name = file.filename.rsplit(".", 1)[0]
    table_name = storage.make_storage_table_name(dataset_name)

    dataset = Dataset(
        name=dataset_name,
        original_filename=file.filename,
        file_type=ext,
        storage_table_name=table_name,
        status="uploaded",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    try:
        storage.persist_dataframe(engine, table_name, df)
        profiles = data_profiling.profile_dataframe(df)
        _save_profile(db, dataset, df, profiles)
        dataset.status = "profiled"
        db.commit()
        db.refresh(dataset)
    except Exception as e:
        logger.exception("Failed to profile/store dataset")
        dataset.status = "error"
        dataset.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to process dataset: {e}")

    return dataset


@router.get("", response_model=list[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(dataset_id: int, limit: int = 50, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    limit = max(1, min(limit, 500))
    try:
        columns, rows = storage.read_preview(engine, dataset.storage_table_name, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset table: {e}")
    return DatasetPreview(columns=columns, rows=rows, total_rows=dataset.row_count)


@router.post("/{dataset_id}/clean", response_model=DatasetDetail)
def clean_dataset(dataset_id: int, options: CleaningOptions, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        df = storage.read_dataframe(engine, dataset.storage_table_name)
        cleaned_df, report = data_cleaning.clean_dataframe(df, options)
        storage.persist_dataframe(engine, dataset.storage_table_name, cleaned_df)
        profiles = data_profiling.profile_dataframe(cleaned_df)
        _save_profile(db, dataset, cleaned_df, profiles)
        dataset.status = "cleaned"
        db.commit()
        db.refresh(dataset)
    except Exception as e:
        logger.exception("Failed to clean dataset")
        raise HTTPException(status_code=500, detail=f"Failed to clean dataset: {e}")

    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    storage.drop_table(engine, dataset.storage_table_name)
    db.delete(dataset)
    db.commit()
    return None


@router.post("/load-sample", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
def load_sample_dataset(db: Session = Depends(get_db)):
    import os
    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data", "sales_sample.csv")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample dataset file not found.")

    with open(sample_path, "rb") as f:
        contents = f.read()

    ext = "csv"
    dataset_name = "sales_sample"
    table_name = storage.make_storage_table_name(dataset_name)

    df = storage.read_upload_to_dataframe(contents, ext)

    dataset = Dataset(
        name=dataset_name,
        original_filename="sales_sample.csv",
        file_type=ext,
        storage_table_name=table_name,
        status="uploaded",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    storage.persist_dataframe(engine, table_name, df)
    profiles = data_profiling.profile_dataframe(df)
    _save_profile(db, dataset, df, profiles)
    dataset.status = "profiled"
    db.commit()
    db.refresh(dataset)

    return dataset

