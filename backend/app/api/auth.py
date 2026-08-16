"""Authentication routes (JWT in HttpOnly cookie)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.jwt import create_access_token
from app.auth.passwords import hash_password, verify_password
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import raise_error
from app.models import User
from app.models.base import UserRole
from app.schemas.auth import LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.post("/register", response_model=UserOut)
def register(
    body: RegisterIn,
    response: Response,
    db: Session = Depends(get_db),
) -> UserOut:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing is not None:
        raise_error(409, "EMAIL_EXISTS", "An account with this email already exists.")

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        role=UserRole.user,
        research_consent=body.research_consent,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_error(409, "EMAIL_EXISTS", "An account with this email already exists.")
    db.refresh(user)

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value,
    )
    _set_auth_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
def login(
    body: LoginIn,
    response: Response,
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise_error(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    if not user.is_active:
        raise_error(403, "ACCOUNT_DISABLED", "This account has been disabled.")

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value,
    )
    _set_auth_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    _clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
