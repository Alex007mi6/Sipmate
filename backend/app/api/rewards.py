"""Rewards catalog and user redemptions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models import Reward, User
from app.schemas.rewards import RedeemOut, RedemptionOut, RewardListOut, RewardOut
from app.services import reward_service

router = APIRouter(prefix="/rewards", tags=["rewards"])


def _redemption_out(redemption, reward: Reward) -> RedemptionOut:
    return RedemptionOut(
        id=redemption.id,
        reward_id=redemption.reward_id,
        reward_name=reward.name,
        points_spent=redemption.points_spent,
        redemption_code=redemption.redemption_code,
        status=redemption.status.value,
        created_at=redemption.created_at,
        redeemed_at=redemption.redeemed_at,
    )


@router.get("", response_model=RewardListOut)
def list_rewards(db: Session = Depends(get_db)) -> RewardListOut:
    items = reward_service.list_rewards(db, active_only=True)
    return RewardListOut(items=[RewardOut.model_validate(r) for r in items])


@router.post("/{reward_id}/redeem", response_model=RedeemOut)
def redeem_reward(
    reward_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedeemOut:
    result = reward_service.redeem_reward(db, user.id, reward_id)
    reward = db.get(Reward, reward_id)
    assert reward is not None
    return RedeemOut(
        redemption=_redemption_out(result.redemption, reward),
        points_balance=result.balance,
    )
