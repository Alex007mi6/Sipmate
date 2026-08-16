"""Gamification: points ledger, badges, lighter-choice acceptance."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import raise_error
from app.models import (
    Badge,
    GamificationRule,
    PointsTransaction,
    Product,
    RecommendationEvent,
    User,
    UserBadge,
)

logger = logging.getLogger("sipmate.gamification")

ACCEPT_EVENT_TYPES = frozenset(
    {"LIGHTER_CHOICE_ACCEPTED", "RECOMMENDATION_ACCEPTED", "ACCEPT_LIGHTER_CHOICE"}
)
UNDO_EVENT_TYPES = frozenset({"LIGHTER_CHOICE_UNDONE", "UNDO_LIGHTER_CHOICE"})
PAIR_AWARD_EVENT_TYPES = ("LIGHTER_CHOICE_ACCEPTED", "ALCOHOL_FREE_CHOICE")
ALCOHOL_FREE_ABV_THRESHOLD = 0.5


@dataclass
class AwardResult:
    awarded: bool = False
    already_awarded: bool = False
    points: int = 0
    badges: list[str] = field(default_factory=list)


def get_points_balance(db: Session, user_id: int) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(PointsTransaction.points), 0)).where(
            PointsTransaction.user_id == user_id
        )
    )
    return int(total or 0)


def _get_rule(db: Session, event_type: str) -> GamificationRule | None:
    return db.scalar(
        select(GamificationRule).where(
            GamificationRule.event_type == event_type,
            GamificationRule.enabled.is_(True),
        )
    )


def _points_already_awarded(
    db: Session,
    user_id: int,
    event_type: str,
    reference_id: str | None,
) -> bool:
    if reference_id is None:
        return False
    existing = db.scalar(
        select(PointsTransaction.id).where(
            PointsTransaction.user_id == user_id,
            PointsTransaction.event_type == event_type,
            PointsTransaction.reference_id == reference_id,
        )
    )
    return existing is not None


def award_points(
    db: Session,
    user_id: int,
    event_type: str,
    reference_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> AwardResult:
    rule = _get_rule(db, event_type)
    if rule is None:
        return AwardResult(awarded=False, points=0)

    points = rule.points
    if points == 0:
        return AwardResult(awarded=False, points=0)

    if _points_already_awarded(db, user_id, event_type, reference_id):
        return AwardResult(awarded=False, already_awarded=True, points=0)

    tx = PointsTransaction(
        user_id=user_id,
        event_type=event_type,
        points=points,
        reference_id=reference_id,
        metadata_json=metadata or {},
    )
    try:
        with db.begin_nested():
            db.add(tx)
            db.flush()
    except IntegrityError:
        return AwardResult(awarded=False, already_awarded=True, points=0)

    badges = evaluate_and_award_badges(db, user_id)
    return AwardResult(awarded=True, points=points, badges=badges)


def _event_count(db: Session, user_id: int, event_type: str) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(PointsTransaction)
        .where(
            PointsTransaction.user_id == user_id,
            PointsTransaction.event_type == event_type,
        )
    )
    return int(count or 0)


def evaluate_and_award_badges(db: Session, user_id: int) -> list[str]:
    counts = {
        "lighter_choice_count": _event_count(db, user_id, "LIGHTER_CHOICE_ACCEPTED"),
        "alcohol_free_choice_count": _event_count(db, user_id, "ALCOHOL_FREE_CHOICE"),
        "ladder_milestone_count": _event_count(db, user_id, "LADDER_MILESTONE"),
    }

    earned_ids = set(
        db.scalars(select(UserBadge.badge_id).where(UserBadge.user_id == user_id)).all()
    )
    badges = list(db.scalars(select(Badge).where(Badge.active.is_(True))).all())
    newly: list[str] = []

    for badge in badges:
        if badge.id in earned_ids:
            continue
        current = counts.get(badge.condition_type)
        if current is None:
            continue
        if current >= badge.threshold:
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
            try:
                db.flush()
                newly.append(badge.name)
                earned_ids.add(badge.id)
            except IntegrityError:
                pass

    return newly


def revoke_badges_no_longer_earned(db: Session, user_id: int) -> list[str]:
    """Remove badges whose thresholds are no longer met after an undo."""
    counts = {
        "lighter_choice_count": _event_count(db, user_id, "LIGHTER_CHOICE_ACCEPTED"),
        "alcohol_free_choice_count": _event_count(db, user_id, "ALCOHOL_FREE_CHOICE"),
        "ladder_milestone_count": _event_count(db, user_id, "LADDER_MILESTONE"),
    }
    revoked: list[str] = []
    rows = list(
        db.scalars(select(UserBadge).where(UserBadge.user_id == user_id)).all()
    )
    for row in rows:
        badge = db.get(Badge, row.badge_id)
        if badge is None or not badge.active:
            continue
        current = counts.get(badge.condition_type)
        if current is None:
            continue
        if current < badge.threshold:
            revoked.append(badge.name)
            db.delete(row)
    if revoked:
        db.flush()
    return revoked


def undo_lighter_choice(
    db: Session,
    user: User | None,
    *,
    selected_id: int,
    recommended_id: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Reverse one Accept: delete award txs for the pair and revoke stale badges."""
    selected = db.get(Product, selected_id)
    recommended = db.get(Product, recommended_id)
    if selected is None or not selected.is_active:
        raise_error(404, "PRODUCT_NOT_FOUND", "Selected product not found.")
    if recommended is None or not recommended.is_active:
        raise_error(404, "PRODUCT_NOT_FOUND", "Recommended product not found.")

    db.add(
        RecommendationEvent(
            user_id=user.id if user else None,
            anonymous_session_id=session_id,
            selected_product_id=selected_id,
            recommended_product_id=recommended_id,
            alcohol_reduction=None,
            event_type="RECOMMENDATION_UNDONE",
        )
    )
    db.flush()

    if user is None:
        db.commit()
        return {
            "ok": True,
            "points_awarded": 0,
            "points_reversed": 0,
            "badges_awarded": [],
            "badges_revoked": [],
            "message": "Undone.",
            "already_awarded": False,
        }

    reference_id = f"{selected_id}:{recommended_id}"
    txs = list(
        db.scalars(
            select(PointsTransaction).where(
                PointsTransaction.user_id == user.id,
                PointsTransaction.event_type.in_(PAIR_AWARD_EVENT_TYPES),
                PointsTransaction.reference_id == reference_id,
            )
        ).all()
    )
    points_reversed = 0
    for tx in txs:
        points_reversed += int(tx.points)
        db.delete(tx)
    if txs:
        db.flush()

    badges_revoked = revoke_badges_no_longer_earned(db, user.id)
    db.commit()
    return {
        "ok": True,
        "points_awarded": 0,
        "points_reversed": points_reversed,
        "badges_awarded": [],
        "badges_revoked": badges_revoked,
        "message": "Undone." if points_reversed or badges_revoked else "Undone (no points to reverse).",
        "already_awarded": False,
    }


def accept_lighter_choice(
    db: Session,
    user: User | None,
    *,
    selected_id: int,
    recommended_id: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    selected = db.get(Product, selected_id)
    recommended = db.get(Product, recommended_id)
    if selected is None or not selected.is_active:
        raise_error(404, "PRODUCT_NOT_FOUND", "Selected product not found.")
    if recommended is None or not recommended.is_active:
        raise_error(404, "PRODUCT_NOT_FOUND", "Recommended product not found.")

    alcohol_reduction: float | None = None
    if selected.alcohol_ml is not None and recommended.alcohol_ml is not None:
        alcohol_reduction = float(selected.alcohol_ml - recommended.alcohol_ml)

    db.add(
        RecommendationEvent(
            user_id=user.id if user else None,
            anonymous_session_id=session_id,
            selected_product_id=selected_id,
            recommended_product_id=recommended_id,
            alcohol_reduction=alcohol_reduction,
            event_type="RECOMMENDATION_ACCEPTED",
        )
    )
    db.flush()

    if user is None:
        db.commit()
        return {
            "ok": True,
            "points_awarded": 0,
            "points_reversed": 0,
            "badges_awarded": [],
            "badges_revoked": [],
            "message": "Log in to save your points and badges.",
            "already_awarded": False,
        }

    reference_id = f"{selected_id}:{recommended_id}"
    total_points = 0
    all_badges: list[str] = []
    already = False

    lighter = award_points(
        db,
        user.id,
        "LIGHTER_CHOICE_ACCEPTED",
        reference_id,
        metadata={"selected_product_id": selected_id, "recommended_product_id": recommended_id},
    )
    if lighter.already_awarded:
        already = True
    if lighter.awarded:
        total_points += lighter.points
        all_badges.extend(lighter.badges)

    if recommended.abv <= ALCOHOL_FREE_ABV_THRESHOLD:
        af = award_points(
            db,
            user.id,
            "ALCOHOL_FREE_CHOICE",
            reference_id,
            metadata={"selected_product_id": selected_id, "recommended_product_id": recommended_id},
        )
        if af.already_awarded:
            already = True
        if af.awarded:
            total_points += af.points
            all_badges.extend(af.badges)

    # Re-evaluate badges once more for any cross-event thresholds
    extra = evaluate_and_award_badges(db, user.id)
    for b in extra:
        if b not in all_badges:
            all_badges.append(b)

    db.commit()
    already_only = already and total_points == 0
    return {
        "ok": True,
        "points_awarded": total_points,
        "points_reversed": 0,
        "badges_awarded": all_badges,
        "badges_revoked": [],
        "message": (
            "Already counted — points were saved for this pair earlier."
            if already_only
            else None
        ),
        "already_awarded": already_only,
    }


def process_gamification_event(
    db: Session,
    user: User | None,
    *,
    event_type: str,
    selected_product_id: int,
    recommended_product_id: int | None,
    session_id: str | None = None,
) -> dict[str, Any]:
    normalized = event_type.upper()

    if normalized in ACCEPT_EVENT_TYPES:
        if recommended_product_id is None:
            raise_error(
                422,
                "MISSING_RECOMMENDED_PRODUCT",
                "recommended_product_id is required for acceptance events.",
            )
        return accept_lighter_choice(
            db,
            user,
            selected_id=selected_product_id,
            recommended_id=recommended_product_id,
            session_id=session_id,
        )

    if normalized in UNDO_EVENT_TYPES:
        if recommended_product_id is None:
            raise_error(
                422,
                "MISSING_RECOMMENDED_PRODUCT",
                "recommended_product_id is required for undo events.",
            )
        return undo_lighter_choice(
            db,
            user,
            selected_id=selected_product_id,
            recommended_id=recommended_product_id,
            session_id=session_id,
        )

    if normalized == "LADDER_MILESTONE":
        db.add(
            RecommendationEvent(
                user_id=user.id if user else None,
                anonymous_session_id=session_id,
                selected_product_id=selected_product_id,
                recommended_product_id=recommended_product_id,
                event_type="LADDER_MILESTONE",
            )
        )
        db.flush()

        if user is None:
            db.commit()
            return {
                "ok": True,
                "points_awarded": 0,
                "points_reversed": 0,
                "badges_awarded": [],
                "badges_revoked": [],
                "message": "Log in to save your points and badges.",
                "already_awarded": False,
            }

        ref = f"ladder:{selected_product_id}:{recommended_product_id or 'none'}"
        result = award_points(
            db,
            user.id,
            "LADDER_MILESTONE",
            ref,
            metadata={"selected_product_id": selected_product_id},
        )
        db.commit()
        return {
            "ok": True,
            "points_awarded": result.points if result.awarded else 0,
            "points_reversed": 0,
            "badges_awarded": result.badges,
            "badges_revoked": [],
            "message": None,
            "already_awarded": result.already_awarded,
        }

    raise_error(422, "UNKNOWN_EVENT_TYPE", f"Unsupported event type: {event_type}")
