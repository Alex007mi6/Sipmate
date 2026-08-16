"""Current user's redemption history."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models import Reward, User
from app.schemas.rewards import RedemptionOut
from app.services import reward_service

router = APIRouter(prefix="/redemptions", tags=["redemptions"])


@router.get("", response_model=list[RedemptionOut])
def list_my_redemptions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RedemptionOut]:
    redemptions = reward_service.list_user_redemptions(db, user.id)
    out: list[RedemptionOut] = []
    for r in redemptions:
        reward = db.get(Reward, r.reward_id)
        out.append(
            RedemptionOut(
                id=r.id,
                reward_id=r.reward_id,
                reward_name=reward.name if reward else "Unknown",
                points_spent=r.points_spent,
                redemption_code=r.redemption_code,
                status=r.status.value,
                created_at=r.created_at,
                redeemed_at=r.redeemed_at,
            )
        )
    return out
