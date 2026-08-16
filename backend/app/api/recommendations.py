from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import raise_error
from app.schemas.products import (
    LadderRequest,
    LadderResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def create_recommendation(
    body: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    result = recommendation_service.recommend_for_product(
        db,
        product_id=body.product_id,
        top_k=body.top_k,
        session_id=body.session_id,
    )
    if result.reason == "PRODUCT_NOT_FOUND":
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")
    return result


@router.post("/ladder", response_model=LadderResponse)
def create_ladder(body: LadderRequest, db: Session = Depends(get_db)) -> LadderResponse:
    selected, steps, reason = recommendation_service.lighter_ladder(
        db, product_id=body.product_id, max_steps=body.max_steps
    )
    if reason == "PRODUCT_NOT_FOUND" or selected is None:
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")
    return LadderResponse(selected=selected, steps=steps)
