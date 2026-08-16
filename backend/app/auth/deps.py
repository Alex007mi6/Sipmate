"""FastAPI auth dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import raise_error
from app.models import User
from app.models.base import UserRole

settings = get_settings()


def get_current_user_optional(
    db: Session = Depends(get_db),
    session: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> User | None:
    if not session:
        return None
    payload = decode_access_token(session)
    if payload is None:
        return None
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise_error(401, "UNAUTHENTICATED", "Authentication required.")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.admin:
        raise_error(403, "FORBIDDEN", "Admin access required.")
    return user
