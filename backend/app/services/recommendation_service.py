"""Recommendation service bridging DB products and offline model artifacts."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, RecommendationEvent
from app.recommender import SipMateRecommender
from app.schemas.products import (
    LadderStepOut,
    ProductOut,
    RecommendationItemOut,
    RecommendationResponse,
)

logger = logging.getLogger("sipmate.recommendation")

ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT / "models"

REASON_MESSAGES = {
    "NO_CANDIDATES": "No suitable lighter alternative was found.",
    "ALREADY_LIGHTEST": "No suitable lighter alternative was found.",
    "MISSING_FEATURES": "This drink cannot be used for taste matching yet.",
    "MODEL_UNAVAILABLE": "Recommendation model is not available.",
    "PRODUCT_NOT_IN_MODEL": "This drink is not in the current recommendation model.",
    "PRODUCT_NOT_FOUND": "Product not found.",
    "NOT_RECOMMENDABLE": "This drink is not eligible for recommendations.",
}


@lru_cache(maxsize=1)
def load_recommender() -> SipMateRecommender | None:
    try:
        model = SipMateRecommender.load(MODELS_DIR)
        logger.info("Loaded recommender with %s products", model.n_products)
        return model
    except Exception:
        logger.exception("Failed to load recommender from %s", MODELS_DIR)
        return None


def reload_recommender() -> SipMateRecommender | None:
    load_recommender.cache_clear()
    return load_recommender()


def _product_id_by_key(db: Session, key: str) -> int | None:
    product = db.scalar(select(Product).where(Product.full_name == key))
    return None if product is None else product.id


def recommend_for_product(
    db: Session,
    *,
    product_id: int,
    top_k: int = 3,
    session_id: str | None = None,
    user_id: int | None = None,
) -> RecommendationResponse:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        return RecommendationResponse(
            selected=ProductOut(
                id=product_id,
                name="",
                full_name="",
                brand="",
                category="",
                description="",
                abv=0,
                serving_ml=None,
                alcohol_ml=None,
                alcohol_grams=None,
                taste_features={},
                image_url=None,
                recommendable=False,
                is_active=False,
            ),
            recommendations=[],
            reason="PRODUCT_NOT_FOUND",
            message=REASON_MESSAGES["PRODUCT_NOT_FOUND"],
        )

    selected_out = ProductOut.model_validate(product)
    if not product.recommendable:
        return RecommendationResponse(
            selected=selected_out,
            recommendations=[],
            reason="NOT_RECOMMENDABLE",
            message=REASON_MESSAGES["NOT_RECOMMENDABLE"],
        )

    model = load_recommender()
    if model is None:
        return RecommendationResponse(
            selected=selected_out,
            recommendations=[],
            reason="MODEL_UNAVAILABLE",
            message=REASON_MESSAGES["MODEL_UNAVAILABLE"],
        )

    result = model.recommend(product.full_name, top_k=top_k)
    items: list[RecommendationItemOut] = []
    for rec in result.recommendations:
        rid = _product_id_by_key(db, rec.product_key)
        if rid is None:
            continue
        items.append(
            RecommendationItemOut(
                product_id=rid,
                product_key=rec.product_key,
                name=rec.name,
                brand=rec.brand,
                category=rec.category,
                abv=rec.abv,
                serving_ml=rec.serving_ml,
                alcohol_ml=rec.alcohol_ml,
                alcohol_grams=rec.alcohol_grams,
                image_url=rec.image_url or None,
                taste_match_pct=round(rec.taste_match_pct, 1),
                cosine_distance=round(rec.cosine_distance, 6),
                abv_reduction=round(rec.abv_reduction, 3),
                abv_reduction_pct=round(rec.abv_reduction_pct, 1),
                alcohol_ml_reduction=(
                    None
                    if rec.alcohol_ml_reduction is None
                    else round(rec.alcohol_ml_reduction, 3)
                ),
                alcohol_ml_reduction_pct=(
                    None
                    if rec.alcohol_ml_reduction_pct is None
                    else round(rec.alcohol_ml_reduction_pct, 1)
                ),
            )
        )
        db.add(
            RecommendationEvent(
                user_id=user_id,
                anonymous_session_id=session_id,
                selected_product_id=product.id,
                recommended_product_id=rid,
                similarity_score=1.0 - rec.cosine_distance,
                alcohol_reduction=rec.alcohol_ml_reduction,
                event_type="RECOMMENDATION_SHOWN",
            )
        )

    reason = result.reason
    if not items and reason is None:
        reason = "NO_CANDIDATES"
    if items:
        db.commit()

    return RecommendationResponse(
        selected=selected_out,
        recommendations=items,
        reason=reason,
        message=None if items else REASON_MESSAGES.get(reason or "", REASON_MESSAGES["NO_CANDIDATES"]),
    )


def lighter_ladder(
    db: Session,
    *,
    product_id: int,
    max_steps: int = 5,
) -> tuple[ProductOut | None, list[LadderStepOut], str | None]:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        return None, [], "PRODUCT_NOT_FOUND"

    model = load_recommender()
    if model is None:
        return ProductOut.model_validate(product), [], "MODEL_UNAVAILABLE"

    raw_steps = model.build_lighter_ladder(product.full_name, max_steps=max_steps)
    steps: list[LadderStepOut] = []
    for step in raw_steps:
        pid = _product_id_by_key(db, step["product_key"])
        steps.append(
            LadderStepOut(
                step=int(step["step"]),
                label=str(step["label"]),
                product_id=pid,
                product_key=str(step["product_key"]),
                name=str(step["name"]),
                abv=float(step["abv"]),
                alcohol_ml=step.get("alcohol_ml"),
                taste_match_pct=step.get("taste_match_pct"),
            )
        )
    return ProductOut.model_validate(product), steps, None
