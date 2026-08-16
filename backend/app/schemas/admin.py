"""Pydantic schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.products import ProductOut
from app.schemas.rewards import RewardOut


class ProductCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=512)
    brand: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=255)
    description: str = ""
    abv: float = Field(ge=0)
    serving_ml: float | None = None
    alcohol_ml: float | None = None
    alcohol_grams: float | None = None
    taste_features: dict[str, Any] = Field(default_factory=dict)
    image_url: str | None = None
    recommendable: bool = True
    is_active: bool = True


class ProductUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=512)
    brand: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    abv: float | None = Field(default=None, ge=0)
    serving_ml: float | None = None
    alcohol_ml: float | None = None
    alcohol_grams: float | None = None
    taste_features: dict[str, Any] | None = None
    image_url: str | None = None
    recommendable: bool | None = None
    is_active: bool | None = None


class ImageUploadOut(BaseModel):
    image_url: str
    image_key: str


class ModelStatusOut(BaseModel):
    loaded: bool
    n_products: int | None = None
    active_version_id: int | None = None
    active_version_status: str | None = None
    stale: bool = False
    product_count: int | None = None
    created_at: datetime | None = None
    activated_at: datetime | None = None


class ModelRebuildOut(BaseModel):
    ok: bool
    version_id: int
    product_count: int
    message: str | None = None


class AdminRedemptionOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    reward_id: int
    reward_name: str
    points_spent: int
    redemption_code: str
    status: str
    created_at: datetime
    redeemed_at: datetime | None


class AdminProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int
