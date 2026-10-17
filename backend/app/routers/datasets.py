from __future__ import annotations

import logging

import io
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas import (
    CleanApplyRequest,
    CleanApplyResponse,
    CleaningOptions,
    CleanPreviewRequest,
    CleanPreviewResponse,
    DatasetDetail,
    DatasetPreview,
    DatasetSummary,
    QualityReportResponse,
    ReportGenerateRequest,
    ReportPreviewResponse,
)
from app.services import data_cleaning, data_profiling, data_quality_detector, gemini_service, report_generator, storage

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
    storage.ensure_raw_backup(engine, table_name)
    profiles = data_profiling.profile_dataframe(df)
    _save_profile(db, dataset, df, profiles)
    dataset.status = "profiled"
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get("/{dataset_id}/quality-audit", response_model=QualityReportResponse)
def audit_dataset_quality(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        storage.ensure_raw_backup(engine, dataset.storage_table_name)
        df = storage.read_dataframe(engine, dataset.storage_table_name)
        issues, quality_score, cat_counts, sev_counts = data_quality_detector.detect_data_quality_issues(
            df, dataset.id, dataset.name
        )

        ai_summary = None
        ai_provider = None

        if issues:
            ai_data = gemini_service.explain_data_quality_report(
                dataset_name=dataset.name,
                issues=[iss.model_dump() for iss in issues],
                quality_score=quality_score,
            )
            if ai_data:
                ai_summary = ai_data.get("ai_summary")
                ai_provider = ai_data.get("ai_provider")
                enhancements = {e.get("id"): e for e in ai_data.get("issue_enhancements", []) if isinstance(e, dict)}
                for iss in issues:
                    if iss.id in enhancements:
                        enh = enhancements[iss.id]
                        if enh.get("why_it_matters"):
                            iss.why_it_matters = str(enh["why_it_matters"]).strip()
                        if enh.get("risks_assumptions"):
                            iss.risks_assumptions = str(enh["risks_assumptions"]).strip()

        return QualityReportResponse(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            total_rows=len(df),
            total_columns=df.shape[1],
            quality_score=quality_score,
            issues_count_by_category=cat_counts,
            issues_count_by_severity=sev_counts,
            total_issues=len(issues),
            issues=issues,
            ai_summary=ai_summary,
            ai_provider=ai_provider,
            has_backup=storage.has_raw_backup(engine, dataset.storage_table_name),
        )
    except Exception as e:
        logger.exception("Failed to audit dataset quality")
        raise HTTPException(status_code=500, detail=f"Failed to audit dataset quality: {e}")


@router.post("/{dataset_id}/clean/preview", response_model=CleanPreviewResponse)
def preview_clean_transforms(dataset_id: int, request: CleanPreviewRequest, db: Session = Depends(get_db)):
    import numpy as np
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        df = storage.read_dataframe(engine, dataset.storage_table_name)
        issues, current_score, _, _ = data_quality_detector.detect_data_quality_issues(
            df, dataset.id, dataset.name
        )

        sample_before = df.head(5).replace({np.nan: None}).to_dict(orient="records")

        # Run preview without modifying database
        preview_df, report = data_cleaning.apply_selected_quality_actions(
            df, request.selected_issue_ids, issues
        )

        # Compute projected quality score
        _, projected_score, _, _ = data_quality_detector.detect_data_quality_issues(
            preview_df, dataset.id, dataset.name
        )

        sample_after = preview_df.head(5).replace({np.nan: None}).to_dict(orient="records")

        return CleanPreviewResponse(
            dataset_id=dataset.id,
            rows_before=report["rows_before"],
            rows_after=report["rows_after"],
            current_quality_score=current_score,
            projected_quality_score=projected_score,
            actions_to_apply=report["actions_applied"],
            sample_before_rows=sample_before,
            sample_after_rows=sample_after,
        )
    except Exception as e:
        logger.exception("Failed to preview cleaning transforms")
        raise HTTPException(status_code=500, detail=f"Failed to preview transforms: {e}")


@router.post("/{dataset_id}/clean/apply", response_model=CleanApplyResponse)
def apply_clean_transforms(dataset_id: int, request: CleanApplyRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if not request.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to apply data transformations.")

    try:
        # Guarantee raw backup is intact before any write
        storage.ensure_raw_backup(engine, dataset.storage_table_name)

        df = storage.read_dataframe(engine, dataset.storage_table_name)
        issues, old_score, _, _ = data_quality_detector.detect_data_quality_issues(
            df, dataset.id, dataset.name
        )

        cleaned_df, report = data_cleaning.apply_selected_quality_actions(
            df, request.selected_issue_ids, issues
        )

        # Persist to working storage table
        storage.persist_dataframe(engine, dataset.storage_table_name, cleaned_df)

        # Re-profile columns
        profiles = data_profiling.profile_dataframe(cleaned_df)
        _save_profile(db, dataset, cleaned_df, profiles)

        _, new_score, _, _ = data_quality_detector.detect_data_quality_issues(
            cleaned_df, dataset.id, dataset.name
        )
        dataset.quality_score = new_score
        dataset.status = "cleaned"
        db.commit()
        db.refresh(dataset)

        summary = f"Successfully applied {len(report['actions_applied'])} transformation(s). Quality score updated from {old_score:.1f} to {new_score:.1f}."

        return CleanApplyResponse(
            dataset_id=dataset.id,
            status="cleaned",
            rows_before=report["rows_before"],
            rows_after=report["rows_after"],
            old_quality_score=old_score,
            new_quality_score=new_score,
            actions_applied=report["actions_applied"],
            applied_report=report,
            summary=summary,
        )
    except Exception as e:
        logger.exception("Failed to apply cleaning transforms")
        raise HTTPException(status_code=500, detail=f"Failed to apply transforms: {e}")


@router.post("/{dataset_id}/clean/reset", response_model=DatasetDetail)
def reset_clean_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        success = storage.restore_raw_backup(engine, dataset.storage_table_name)
        if not success:
            raise HTTPException(status_code=400, detail="No original snapshot exists to restore from.")

        df = storage.read_dataframe(engine, dataset.storage_table_name)
        profiles = data_profiling.profile_dataframe(df)
        _save_profile(db, dataset, df, profiles)
        dataset.status = "profiled"
        db.commit()
        db.refresh(dataset)
        return dataset
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to reset dataset to original")
        raise HTTPException(status_code=500, detail=f"Failed to reset dataset: {e}")


@router.get("/{dataset_id}/export")
def export_dataset(dataset_id: int, format: str = Query("csv", pattern="^(csv|xlsx)$"), db: Session = Depends(get_db)):
    import re
    import pandas as pd
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        df = storage.read_dataframe(engine, dataset.storage_table_name)
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", dataset.name)

        if format == "xlsx":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Data")
            output.seek(0)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{clean_name}_clean.xlsx"
            return StreamingResponse(
                output,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        else:
            csv_str = df.to_csv(index=False)
            output = io.BytesIO(csv_str.encode("utf-8"))
            media_type = "text/csv"
            filename = f"{clean_name}_clean.csv"
            return StreamingResponse(
                output,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
    except Exception as e:
        logger.exception("Failed to export dataset")
        raise HTTPException(status_code=500, detail=f"Failed to export dataset: {e}")


@router.post("/{dataset_id}/report/preview", response_model=ReportPreviewResponse)
def preview_executive_report(dataset_id: int, request: ReportGenerateRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        raise HTTPException(status_code=400, detail="Dataset has no columns profiled.")

    try:
        report_data = report_generator.compile_report_data(
            engine=engine,
            dataset=dataset,
            columns=columns,
            target_column=request.target_column,
            date_column=request.date_column,
            horizon=request.forecast_horizon,
            sections=request.sections.model_dump(),
        )

        return ReportPreviewResponse(
            title=request.title or "Executive Business Intelligence Report",
            subtitle=request.subtitle or f"Synthesized Portfolio Performance for {dataset.name}",
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            total_rows=report_data["total_rows"],
            total_columns=report_data["total_columns"],
            quality_score=report_data["quality_score"],
            primary_metric=report_data["primary_metric"],
            narrative=report_data["narrative"],
            distribution=report_data["distribution"],
            top_categories=report_data["top_categories"],
            quality_issues=report_data["quality_issues"],
            insights=report_data["insights"],
            forecast=report_data["forecast"],
            sections=report_data["sections"],
        )
    except Exception as e:
        logger.exception("Failed to compile executive report preview")
        raise HTTPException(status_code=500, detail=f"Failed to compile report preview: {e}")


@router.post("/{dataset_id}/report/pdf")
def generate_executive_report_pdf(dataset_id: int, request: ReportGenerateRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    columns = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not columns:
        raise HTTPException(status_code=400, detail="Dataset has no columns profiled.")

    try:
        report_data = report_generator.compile_report_data(
            engine=engine,
            dataset=dataset,
            columns=columns,
            target_column=request.target_column,
            date_column=request.date_column,
            horizon=request.forecast_horizon,
            sections=request.sections.model_dump(),
        )

        pdf_bytes = report_generator.generate_executive_pdf(
            report_data=report_data,
            title=request.title or "Executive Business Intelligence Report",
            subtitle=request.subtitle,
        )

        import datetime as _dt
        import re as _re
        clean_ds_name = _re.sub(r"[^a-zA-Z0-9_\-]", "_", dataset.name)
        date_stamp = _dt.date.today().strftime("%Y%m%d")
        filename = f"InsightAI_Report_{clean_ds_name}_{date_stamp}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.exception("Failed to generate executive PDF report")
        raise HTTPException(status_code=500, detail=f"Failed to generate executive report: {e}")


