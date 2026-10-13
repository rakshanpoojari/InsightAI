import datetime as dt

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # csv | xlsx
    storage_table_name = Column(String, nullable=False, unique=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    status = Column(String, default="uploaded")  # uploaded | profiled | cleaned | error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String, nullable=False)
    inferred_type = Column(String, nullable=False)  # numeric | categorical | datetime | boolean | text
    missing_count = Column(Integer, default=0)
    missing_pct = Column(Float, default=0.0)
    unique_count = Column(Integer, default=0)
    sample_values = Column(JSON, default=list)
    stats = Column(JSON, default=dict)  # min/max/mean/std for numeric, top values for categorical

    dataset = relationship("Dataset", back_populates="columns")
