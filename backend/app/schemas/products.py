"""Pydantic schemas for products and recommendations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: int
    name: str
    full_name: str
    brand: str
    category: str
    description: str
    abv: float
    serving_ml: float | None
    alcohol_ml: float | None
    alcohol_grams: float | None
    taste_features: dict[str, Any]
    image_url: str | None
    recommendable: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


class RecommendationRequest(BaseModel):
    product_id: int
    top_k: int = Field(default=3, ge=1, le=10)
    session_id: str | None = None


class RecommendationItemOut(BaseModel):
    product_id: int
    product_key: str
    name: str
    brand: str
    category: str
    abv: float
    serving_ml: float | None
    alcohol_ml: float | None
    alcohol_grams: float | None
    image_url: str | None
    taste_match_pct: float
    cosine_distance: float
    abv_reduction: float
    abv_reduction_pct: float
    alcohol_ml_reduction: float | None
    alcohol_ml_reduction_pct: float | None


class RecommendationResponse(BaseModel):
    selected: ProductOut
    recommendations: list[RecommendationItemOut]
    reason: str | None = None
    message: str | None = None


class LadderRequest(BaseModel):
    product_id: int
    max_steps: int = Field(default=5, ge=1, le=10)


class LadderStepOut(BaseModel):
    step: int
    label: str
    product_id: int | None = None
    product_key: str
    name: str
    abv: float
    alcohol_ml: float | None
    taste_match_pct: float | None = None


class LadderResponse(BaseModel):
    selected: ProductOut
    steps: list[LadderStepOut]
