"""Shared SQLAlchemy mixins / enums."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class ModelStatus(str, enum.Enum):
    active = "active"
    stale = "stale"
    archived = "archived"
    failed = "failed"


class RedemptionStatus(str, enum.Enum):
    pending = "pending"
    redeemed = "redeemed"
    cancelled = "cancelled"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
