"""Rewards catalog and redemption."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import raise_error
from app.models import PointsTransaction, Redemption, Reward
from app.models.base import RedemptionStatus
from app.services.gamification_service import get_points_balance


@dataclass
class RedeemResult:
    redemption: Redemption
    balance: int


def list_rewards(db: Session, *, active_only: bool = True) -> list[Reward]:
    stmt = select(Reward).order_by(Reward.points_cost, Reward.name)
    if active_only:
        stmt = stmt.where(Reward.active.is_(True))
    return list(db.scalars(stmt).all())


def list_user_redemptions(db: Session, user_id: int) -> list[Redemption]:
    return list(
        db.scalars(
            select(Redemption)
            .where(Redemption.user_id == user_id)
            .order_by(Redemption.created_at.desc())
        ).all()
    )


def _generate_code() -> str:
    return secrets.token_hex(8).upper()


def redeem_reward(db: Session, user_id: int, reward_id: int) -> RedeemResult:
    reward = db.get(Reward, reward_id)
    if reward is None or not reward.active:
        raise_error(404, "REWARD_NOT_FOUND", "Reward not found.")
    if reward.stock <= 0:
        raise_error(409, "OUT_OF_STOCK", "This reward is out of stock.")

    balance = get_points_balance(db, user_id)
    if balance < reward.points_cost:
        raise_error(
            409,
            "INSUFFICIENT_POINTS",
            "Not enough points.",
            details={"balance": balance, "required": reward.points_cost},
        )

    code = _generate_code()
    reference_id = f"redeem:{reward_id}:{code}"

    try:
        db.add(
            PointsTransaction(
                user_id=user_id,
                event_type="REWARD_REDEMPTION",
                points=-reward.points_cost,
                reference_id=reference_id,
                metadata_json={"reward_id": reward_id, "redemption_code": code},
            )
        )
        db.flush()

        new_balance = get_points_balance(db, user_id)
        if new_balance < 0:
            db.rollback()
            raise_error(409, "INSUFFICIENT_POINTS", "Not enough points.")

        reward.stock -= 1
        redemption = Redemption(
            user_id=user_id,
            reward_id=reward_id,
            points_spent=reward.points_cost,
            redemption_code=code,
            status=RedemptionStatus.pending,
        )
        db.add(redemption)
        db.commit()
        db.refresh(redemption)
        return RedeemResult(redemption=redemption, balance=new_balance)
    except IntegrityError:
        db.rollback()
        raise_error(409, "REDEEM_CONFLICT", "Redemption could not be completed.")
