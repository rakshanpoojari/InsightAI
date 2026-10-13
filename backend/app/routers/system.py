from __future__ import annotations

import os
import sys
import duckdb
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models.dataset import Dataset

router = APIRouter(prefix="/api/system", tags=["system"])


def _format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    # 1. Inspect SQLite storage
    with engine.connect() as conn:
        table_rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()
        tables = [row[0] for row in table_rows]

    db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")
    file_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    # 2. Datasets & row metrics
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    total_records = sum(d.row_count or 0 for d in datasets)

    dataset_metrics = [
        {
            "id": d.id,
            "name": d.name,
            "storage_table_name": d.storage_table_name,
            "row_count": d.row_count or 0,
            "column_count": d.column_count or 0,
            "quality_score": d.quality_score or 0.0,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in datasets
    ]

    # 3. DuckDB operational stats
    duckdb_ver = duckdb.__version__

    return {
        "status": "healthy",
        "sqlite": {
            "status": "operational",
            "role": "Persistent Storage & Metadata Catalog",
            "engine": "SQLite 3",
            "database_file": db_path,
            "file_size_bytes": file_size_bytes,
            "file_size_formatted": _format_bytes(file_size_bytes),
            "total_tables": len(tables),
            "tables": tables,
        },
        "duckdb": {
            "status": "operational",
            "role": "Vectorized In-Memory Analytical OLAP Engine",
            "version": duckdb_ver,
            "capabilities": [
                "SIMD Vectorized Columnar Processing",
                "Sub-millisecond Aggregations & Group-By",
                "Native Pearson Correlation (CORR)",
                "Zero-Copy Arrow & Pandas Register",
                "Window Functions & CTE Execution",
            ],
        },
        "datasets_summary": {
            "total_datasets": len(datasets),
            "total_records": total_records,
            "datasets": dataset_metrics,
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "api_service": "FastAPI (InsightAI Core)",
            "ai_mode": (
                "Hybrid (LLM Configured + Deterministic Heuristics)"
                if settings.gemini_api_key or settings.openai_api_key
                else "Deterministic Intelligence Core (Heuristics + Scikit-Learn ML)"
            ),
        },
    }
