"""Gamification event ingestion."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user_optional
from app.core.db import get_db
from app.models import User
from app.schemas.profile import GamificationEventIn, GamificationEventOut
from app.services import gamification_service

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.post("/events", response_model=GamificationEventOut)
def post_gamification_event(
    body: GamificationEventIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> GamificationEventOut:
    result = gamification_service.process_gamification_event(
        db,
        user,
        event_type=body.event_type,
        selected_product_id=body.selected_product_id,
        recommended_product_id=body.recommended_product_id,
        session_id=body.session_id,
    )
    return GamificationEventOut(**result)
