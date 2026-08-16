"""API smoke tests for products + recommendations (SQLite)."""

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

# Ensure tests don't require external Postgres
os.environ["DATABASE_URL"] = "sqlite://"

from app.core.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Product  # noqa: E402
from app.recommender.features import TASTE_FEATURES  # noqa: E402
from app.services import recommendation_service  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def _taste(seed: int) -> dict:
        return {f: float((seed * (i + 3)) % 50) for i, f in enumerate(TASTE_FEATURES)}

    with TestingSession() as db:
        products = [
            Product(
                name="Heavy",
                full_name="Test Brew Heavy",
                brand="Test Brew",
                category="Stout",
                description="",
                abv=8.0,
                serving_ml=375,
                alcohol_ml=30.0,
                alcohol_grams=23.67,
                taste_features=_taste(1),
                recommendable=True,
                is_active=True,
            ),
            Product(
                name="Mid",
                full_name="Test Brew Mid",
                brand="Test Brew",
                category="Stout",
                description="",
                abv=5.0,
                serving_ml=375,
                alcohol_ml=18.75,
                alcohol_grams=14.79,
                taste_features=_taste(1),  # similar taste
                recommendable=True,
                is_active=True,
            ),
            Product(
                name="Light",
                full_name="Test Brew Light",
                brand="Other",
                category="Lager",
                description="",
                abv=3.0,
                serving_ml=375,
                alcohol_ml=11.25,
                alcohol_grams=8.87,
                taste_features=_taste(9),
                recommendable=True,
                is_active=True,
            ),
        ]
        db.add_all(products)
        db.commit()

        # Fit an in-memory recommender on these products and monkeypatch loader
        import pandas as pd
        from app.recommender import SipMateRecommender

        rows = []
        for p in db.query(Product).all():
            row = {
                "full_name": p.full_name,
                "name": p.name,
                "brand": p.brand,
                "category": p.category,
                "abv": p.abv,
                "serving_ml": p.serving_ml,
                "alcohol_ml": p.alcohol_ml,
                "alcohol_grams": p.alcohol_grams,
                "image_url": "",
                "recommendable": True,
            }
            row.update(p.taste_features)
            rows.append(row)
        model = SipMateRecommender().fit(pd.DataFrame(rows))
        model_dir = tmp_path / "models"
        model.save(model_dir)
        recommendation_service.MODELS_DIR = model_dir
        recommendation_service.load_recommender.cache_clear()

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
    recommendation_service.load_recommender.cache_clear()


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_and_get_products(client: TestClient):
    res = client.get("/api/products?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    pid = body["items"][0]["id"]
    detail = client.get(f"/api/products/{pid}")
    assert detail.status_code == 200
    assert detail.json()["id"] == pid


def test_recommendation_constraint(client: TestClient):
    products = client.get("/api/products").json()["items"]
    heavy = next(p for p in products if p["name"] == "Heavy")
    res = client.post(
        "/api/recommendations",
        json={"product_id": heavy["id"], "top_k": 2, "session_id": "test-session"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["reason"] is None
    assert body["recommendations"]
    for rec in body["recommendations"]:
        assert rec["alcohol_ml"] < heavy["alcohol_ml"]
        assert rec["product_id"] != heavy["id"]


def test_no_recommendation_for_lightest(client: TestClient):
    products = client.get("/api/products").json()["items"]
    light = next(p for p in products if p["name"] == "Light")
    res = client.post("/api/recommendations", json={"product_id": light["id"]})
    assert res.status_code == 200
    body = res.json()
    assert body["recommendations"] == []
    assert body["reason"] == "NO_CANDIDATES"
    assert "lighter" in (body["message"] or "").lower()
