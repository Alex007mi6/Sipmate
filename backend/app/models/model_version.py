from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.core.db import Base
from app.models.base import ModelStatus

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    feature_names: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    dataset_version: Mapped[str] = mapped_column(String(120), nullable=False)
    model_path: Mapped[str] = mapped_column(String(512), nullable=False)
    scaler_path: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, name="model_status"), nullable=False, default=ModelStatus.active
    )
    product_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
