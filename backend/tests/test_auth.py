"""Authentication API tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

os.environ["DATABASE_URL"] = "sqlite://"

from app.core.config import get_settings  # noqa: E402
from app.core.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_login_me_logout(client: TestClient):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "user@example.com",
            "password": "password123",
            "display_name": "Test User",
        },
    )
    assert reg.status_code == 200
    body = reg.json()
    assert body["email"] == "user@example.com"
    assert get_settings().cookie_name in reg.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Test User"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 401


def test_login_and_invalid_credentials(client: TestClient):
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "display_name": "Login User",
        },
    )
    client.post("/api/auth/logout")

    ok = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert ok.status_code == 200
    assert ok.cookies.get(get_settings().cookie_name)

    bad = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_duplicate_email(client: TestClient):
    payload = {
        "email": "dup@example.com",
        "password": "password123",
        "display_name": "Dup",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 200
    dup = client.post("/api/auth/register", json=payload)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "EMAIL_EXISTS"
