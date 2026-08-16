"""Points balance and reward redemption tests."""

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

from app.auth.passwords import hash_password  # noqa: E402
from app.core.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import GamificationRule, PointsTransaction, Product, Reward, User  # noqa: E402
from app.models.base import UserRole  # noqa: E402
from app.recommender.features import TASTE_FEATURES  # noqa: E402


def _taste(seed: int) -> dict:
    return {f: float((seed * (i + 3)) % 50) for i, f in enumerate(TASTE_FEATURES)}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSession() as db:
        db.add_all(
            [
                GamificationRule(
                    event_type="LIGHTER_CHOICE_ACCEPTED",
                    points=10,
                    cooldown_seconds=0,
                    enabled=True,
                    metadata_json={},
                ),
                GamificationRule(
                    event_type="ALCOHOL_FREE_CHOICE",
                    points=20,
                    cooldown_seconds=0,
                    enabled=True,
                    metadata_json={},
                ),
                GamificationRule(
                    event_type="REWARD_REDEMPTION",
                    points=0,
                    cooldown_seconds=0,
                    enabled=True,
                    metadata_json={},
                ),
            ]
        )
        heavy = Product(
            name="Heavy",
            full_name="Test Heavy",
            brand="Test",
            category="Stout",
            description="",
            abv=8.0,
            serving_ml=375,
            alcohol_ml=30.0,
            alcohol_grams=23.67,
            taste_features=_taste(1),
            recommendable=True,
            is_active=True,
        )
        light = Product(
            name="Light",
            full_name="Test Light",
            brand="Test",
            category="Lager",
            description="",
            abv=3.0,
            serving_ml=375,
            alcohol_ml=11.25,
            alcohol_grams=8.87,
            taste_features=_taste(2),
            recommendable=True,
            is_active=True,
        )
        db.add_all([heavy, light])
        db.flush()

        user = User(
            email="points@example.com",
            password_hash=hash_password("password123"),
            display_name="Points User",
            role=UserRole.user,
            is_active=True,
        )
        poor = User(
            email="poor@example.com",
            password_hash=hash_password("password123"),
            display_name="Poor User",
            role=UserRole.user,
            is_active=True,
        )
        db.add_all([user, poor])
        db.flush()
        db.add(
            PointsTransaction(
                user_id=user.id,
                event_type="TEST_SETUP",
                points=30,
                reference_id="setup-points-user",
                metadata_json={},
            )
        )
        db.add(
            Reward(
                name="Snack",
                description="A snack",
                points_cost=30,
                stock=2,
                active=True,
            )
        )
        db.commit()

        product_ids = {
            "heavy": db.query(Product).filter_by(name="Heavy").one().id,
            "light": db.query(Product).filter_by(name="Light").one().id,
        }
        reward_id = db.query(Reward).one().id

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, product_ids, reward_id
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str, password: str = "password123") -> None:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200


def _award_points(client: TestClient, heavy_id: int, light_id: int, times: int = 1) -> None:
    for i in range(times):
        res = client.post(
            "/api/gamification/events",
            json={
                "event_type": "LIGHTER_CHOICE_ACCEPTED",
                "selected_product_id": heavy_id,
                "recommended_product_id": light_id,
                "session_id": f"sess-{i}",
            },
        )
        assert res.status_code == 200


def test_insufficient_points(client):
    c, _, reward_id = client
    _login(c, "poor@example.com")
    res = c.post(f"/api/rewards/{reward_id}/redeem")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "INSUFFICIENT_POINTS"


def test_successful_redemption(client):
    c, _, reward_id = client
    _login(c, "points@example.com")

    balance = c.get("/api/profile/points").json()["balance"]
    assert balance == 30

    res = c.post(f"/api/rewards/{reward_id}/redeem")
    assert res.status_code == 200
    body = res.json()
    assert body["points_balance"] == 0
    assert body["redemption"]["redemption_code"]
    assert body["redemption"]["status"] == "pending"


def test_duplicate_points_prevention(client):
    c, product_ids, _ = client
    _login(c, "poor@example.com")

    payload = {
        "event_type": "LIGHTER_CHOICE_ACCEPTED",
        "selected_product_id": product_ids["heavy"],
        "recommended_product_id": product_ids["light"],
    }
    first = c.post("/api/gamification/events", json=payload)
    assert first.status_code == 200
    assert first.json()["points_awarded"] == 10

    second = c.post("/api/gamification/events", json=payload)
    assert second.status_code == 200
    assert second.json()["points_awarded"] == 0
    assert second.json()["already_awarded"] is True

    balance = c.get("/api/profile/points").json()["balance"]
    assert balance == 10


def test_undo_reverses_points_and_allows_reaward(client):
    c, product_ids, _ = client
    _login(c, "poor@example.com")
    heavy = product_ids["heavy"]
    light = product_ids["light"]

    accept = c.post(
        "/api/gamification/events",
        json={
            "event_type": "LIGHTER_CHOICE_ACCEPTED",
            "selected_product_id": heavy,
            "recommended_product_id": light,
        },
    )
    assert accept.status_code == 200
    assert accept.json()["points_awarded"] == 10
    assert c.get("/api/profile/points").json()["balance"] == 10

    undo = c.post(
        "/api/gamification/events",
        json={
            "event_type": "LIGHTER_CHOICE_UNDONE",
            "selected_product_id": heavy,
            "recommended_product_id": light,
        },
    )
    assert undo.status_code == 200
    body = undo.json()
    assert body["points_reversed"] == 10
    assert c.get("/api/profile/points").json()["balance"] == 0

    again = c.post(
        "/api/gamification/events",
        json={
            "event_type": "LIGHTER_CHOICE_ACCEPTED",
            "selected_product_id": heavy,
            "recommended_product_id": light,
        },
    )
    assert again.status_code == 200
    assert again.json()["points_awarded"] == 10
    assert c.get("/api/profile/points").json()["balance"] == 10


def test_sequential_double_redeem(client):
    c, _, reward_id = client
    _login(c, "points@example.com")

    first = c.post(f"/api/rewards/{reward_id}/redeem")
    assert first.status_code == 200

    second = c.post(f"/api/rewards/{reward_id}/redeem")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INSUFFICIENT_POINTS"

    balance = c.get("/api/profile/points").json()["balance"]
    assert balance == 0
