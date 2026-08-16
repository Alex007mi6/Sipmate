"""Pydantic schemas for profile and gamification."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.auth import UserOut


class BadgeOut(BaseModel):
    id: int
    name: str
    description: str
    icon: str
    earned_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    user: UserOut
    points_balance: int
    badges: list[BadgeOut]


class PointsBalanceOut(BaseModel):
    balance: int


class PointsTransactionOut(BaseModel):
    id: int
    event_type: str
    points: int
    reference_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GamificationEventIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    selected_product_id: int
    recommended_product_id: int | None = None
    session_id: str | None = Field(default=None, max_length=64)


class GamificationEventOut(BaseModel):
    ok: bool = True
    points_awarded: int = 0
    points_reversed: int = 0
    badges_awarded: list[str] = Field(default_factory=list)
    badges_revoked: list[str] = Field(default_factory=list)
    message: str | None = None
    already_awarded: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
