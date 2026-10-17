from __future__ import annotations

import io
import re
import uuid

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def get_extension(filename: str) -> str:
    if "." not in filename:
        raise ValueError("File has no extension.")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '.{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    return ext


def read_upload_to_dataframe(file_bytes: bytes, ext: str) -> pd.DataFrame:
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))

    if df.empty:
        raise ValueError("Uploaded file contains no rows.")
    if df.shape[1] == 0:
        raise ValueError("Uploaded file contains no columns.")

    # Normalize column names: no leading/trailing whitespace, no duplicate names
    df.columns = [str(c).strip() for c in df.columns]
    seen = {}
    new_cols = []
    for c in df.columns:
        if c in seen:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            new_cols.append(c)
    df.columns = new_cols
    return df


def make_storage_table_name(dataset_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", dataset_name.lower())[:40]
    return f"ds_{slug}_{uuid.uuid4().hex[:8]}"


def persist_dataframe(engine: Engine, table_name: str, df: pd.DataFrame) -> None:
    # if_exists="replace" is safe here because table_name is unique per dataset version
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)


def read_dataframe(engine: Engine, table_name: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_table(table_name, con=conn)


def read_preview(engine: Engine, table_name: str, limit: int = 50) -> tuple[list[str], list[dict]]:
    with engine.connect() as conn:
        result = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit'), {"limit": limit})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return columns, rows


def drop_table(engine: Engine, table_name: str) -> None:
    raw_table = get_raw_table_name(table_name)
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{raw_table}"'))


def get_raw_table_name(table_name: str) -> str:
    return f"raw_{table_name}"


def ensure_raw_backup(engine: Engine, table_name: str) -> None:
    raw_table = get_raw_table_name(table_name)
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": raw_table},
        ).scalar()
        if not exists:
            src_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                {"t": table_name},
            ).scalar()
            if src_exists:
                conn.execute(text(f'CREATE TABLE "{raw_table}" AS SELECT * FROM "{table_name}"'))


def restore_raw_backup(engine: Engine, table_name: str) -> bool:
    raw_table = get_raw_table_name(table_name)
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": raw_table},
        ).scalar()
        if not exists:
            return False
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.execute(text(f'CREATE TABLE "{table_name}" AS SELECT * FROM "{raw_table}"'))
        return True


def has_raw_backup(engine: Engine, table_name: str) -> bool:
    raw_table = get_raw_table_name(table_name)
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": raw_table},
        ).scalar()
        return bool(exists)
