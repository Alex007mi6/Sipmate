"""Pydantic schemas for rewards and redemptions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RewardOut(BaseModel):
    id: int
    name: str
    description: str
    image_url: str | None
    points_cost: int
    stock: int
    active: bool

    model_config = {"from_attributes": True}


class RewardListOut(BaseModel):
    items: list[RewardOut]


class RedemptionOut(BaseModel):
    id: int
    reward_id: int
    reward_name: str
    points_spent: int
    redemption_code: str
    status: str
    created_at: datetime
    redeemed_at: datetime | None

    model_config = {"from_attributes": True}


class RedeemOut(BaseModel):
    redemption: RedemptionOut
    points_balance: int


class RewardCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    points_cost: int = Field(ge=1)
    stock: int = Field(ge=0, default=0)
    active: bool = True
    image_url: str | None = None


class RewardUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    points_cost: int | None = Field(default=None, ge=1)
    stock: int | None = Field(default=None, ge=0)
    active: bool | None = None
    image_url: str | None = None
