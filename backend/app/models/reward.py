from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import RedemptionStatus, TimestampMixin


class Reward(Base, TimestampMixin):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    redemptions = relationship("Redemption", back_populates="reward")


class Redemption(Base):
    __tablename__ = "redemptions"
    __table_args__ = (UniqueConstraint("redemption_code", name="uq_redemption_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"), nullable=False, index=True)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    redemption_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[RedemptionStatus] = mapped_column(
        Enum(RedemptionStatus, name="redemption_status"),
        nullable=False,
        default=RedemptionStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="redemptions")
    reward = relationship("Reward", back_populates="redemptions")
