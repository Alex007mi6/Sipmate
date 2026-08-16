"""User profile and gamification summary routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models import Badge, User, UserBadge
from app.schemas.auth import UserOut
from app.schemas.profile import BadgeOut, PointsBalanceOut, ProfileOut
from app.services import gamification_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    balance = gamification_service.get_points_balance(db, user.id)
    rows = db.execute(
        select(Badge, UserBadge.earned_at)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user.id)
        .order_by(UserBadge.earned_at.desc())
    ).all()
    badges = [
        BadgeOut(
            id=badge.id,
            name=badge.name,
            description=badge.description,
            icon=badge.icon,
            earned_at=earned_at,
        )
        for badge, earned_at in rows
    ]
    return ProfileOut(
        user=UserOut.model_validate(user),
        points_balance=balance,
        badges=badges,
    )


@router.get("/points", response_model=PointsBalanceOut)
def get_points(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PointsBalanceOut:
    return PointsBalanceOut(balance=gamification_service.get_points_balance(db, user.id))


@router.get("/badges", response_model=list[BadgeOut])
def get_badges(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BadgeOut]:
    rows = db.execute(
        select(Badge, UserBadge.earned_at)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user.id)
        .order_by(UserBadge.earned_at.desc())
    ).all()
    return [
        BadgeOut(
            id=badge.id,
            name=badge.name,
            description=badge.description,
            icon=badge.icon,
            earned_at=earned_at,
        )
        for badge, earned_at in rows
    ]
