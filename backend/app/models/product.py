from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.base import TimestampMixin

# JSON works on SQLite tests; PostgreSQL dialect prefers JSONB via migration.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("full_name", name="uq_products_full_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    abv: Mapped[float] = mapped_column(Float, nullable=False)
    serving_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    alcohol_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    alcohol_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    taste_features: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Import flags retained for admin review
    abv_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missing_taste_profile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommendable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
