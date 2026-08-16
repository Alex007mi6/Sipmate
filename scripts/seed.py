"""
Seed demo admin, badges, gamification rules, and sample rewards.

Admin credentials come from environment variables (see .env.example).
Do not commit real production passwords.

Usage (repo root):
    py -3 scripts/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.auth.passwords import hash_password  # noqa: E402
from app.models import Badge, GamificationRule, Reward, User  # noqa: E402
from app.models.base import UserRole  # noqa: E402


RULES = [
    {"event_type": "LIGHTER_CHOICE_ACCEPTED", "points": 10, "cooldown_seconds": 0},
    {"event_type": "ALCOHOL_FREE_CHOICE", "points": 20, "cooldown_seconds": 0},
    {"event_type": "LADDER_MILESTONE", "points": 15, "cooldown_seconds": 0},
]

BADGES = [
    {
        "name": "First Lighter Step",
        "description": "Accepted your first lower-alcohol alternative.",
        "icon": "first-lighter",
        "condition_type": "lighter_choice_count",
        "threshold": 1,
    },
    {
        "name": "Lighter Explorer",
        "description": "Completed 3 valid lighter choices.",
        "icon": "lighter-explorer",
        "condition_type": "lighter_choice_count",
        "threshold": 3,
    },
    {
        "name": "Ladder Climber",
        "description": "Reached a Lighter Ladder milestone.",
        "icon": "ladder-climber",
        "condition_type": "ladder_milestone_count",
        "threshold": 1,
    },
    {
        "name": "Zero Hero",
        "description": "Chose an alcohol-free alternative.",
        "icon": "zero-hero",
        "condition_type": "alcohol_free_choice_count",
        "threshold": 1,
    },
]

REWARDS = [
    {
        "name": "Alcohol-Free Soft Drink",
        "description": "Prototype voucher for one alcohol-free soft drink.",
        "points_cost": 40,
        "stock": 50,
    },
    {
        "name": "Pub Snack",
        "description": "Prototype voucher for a small snack.",
        "points_cost": 30,
        "stock": 50,
    },
    {
        "name": "Zero-Alcohol Beer Token",
        "description": "Prototype voucher for one alcohol-free beer.",
        "points_cost": 60,
        "stock": 25,
    },
]


def upsert_admin(db: Session) -> str:
    settings = get_settings()
    existing = db.scalar(select(User).where(User.email == settings.admin_email))
    password_hash = hash_password(settings.admin_password)
    if existing is None:
        db.add(
            User(
                email=settings.admin_email,
                password_hash=password_hash,
                display_name=settings.admin_display_name,
                role=UserRole.admin,
                is_active=True,
            )
        )
        return "created"
    existing.password_hash = password_hash
    existing.display_name = settings.admin_display_name
    existing.role = UserRole.admin
    existing.is_active = True
    return "updated"


def seed_rules(db: Session) -> tuple[int, int]:
    created = updated = 0
    for rule in RULES:
        row = db.scalar(
            select(GamificationRule).where(GamificationRule.event_type == rule["event_type"])
        )
        if row is None:
            db.add(
                GamificationRule(
                    event_type=rule["event_type"],
                    points=rule["points"],
                    cooldown_seconds=rule["cooldown_seconds"],
                    enabled=True,
                    metadata_json={},
                )
            )
            created += 1
        else:
            row.points = rule["points"]
            row.cooldown_seconds = rule["cooldown_seconds"]
            row.enabled = True
            updated += 1
    return created, updated


def seed_badges(db: Session) -> tuple[int, int]:
    created = updated = 0
    for badge in BADGES:
        row = db.scalar(select(Badge).where(Badge.name == badge["name"]))
        if row is None:
            db.add(Badge(**badge, active=True))
            created += 1
        else:
            for k, v in badge.items():
                setattr(row, k, v)
            row.active = True
            updated += 1
    return created, updated


def seed_rewards(db: Session) -> tuple[int, int]:
    created = updated = 0
    for reward in REWARDS:
        row = db.scalar(select(Reward).where(Reward.name == reward["name"]))
        if row is None:
            db.add(Reward(**reward, active=True))
            created += 1
        else:
            for k, v in reward.items():
                setattr(row, k, v)
            row.active = True
            updated += 1
    return created, updated


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        admin_status = upsert_admin(db)
        rules_c, rules_u = seed_rules(db)
        badges_c, badges_u = seed_badges(db)
        rewards_c, rewards_u = seed_rewards(db)
        db.commit()
    finally:
        db.close()

    print("Seed complete")
    print(f"  admin ({settings.admin_email}): {admin_status}")
    print(f"  rules: created={rules_c} updated={rules_u}")
    print(f"  badges: created={badges_c} updated={badges_u}")
    print(f"  rewards: created={rewards_c} updated={rewards_u}")
    print("  NOTE: admin password taken from ADMIN_PASSWORD env / .env")


if __name__ == "__main__":
    main()
