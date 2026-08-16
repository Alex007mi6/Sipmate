"""Unit tests for constraint-based SipMate recommender."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.recommender import SipMateRecommender
from app.recommender.features import TASTE_FEATURES


def _tiny_catalog() -> pd.DataFrame:
    # Three beers; middle ABV should recommend the lighter similar one.
    rows = [
        {
            "full_name": "Brew A Heavy",
            "name": "Heavy",
            "brand": "Brew A",
            "category": "Stout",
            "abv": 8.0,
            "serving_ml": 375.0,
            "alcohol_ml": 375.0 * 8.0 / 100.0,
            "alcohol_grams": 375.0 * 8.0 / 100.0 * 0.789,
            "image_url": "",
            "recommendable": True,
            "astringency": 10,
            "body": 80,
            "bitter": 40,
            "sweet": 50,
            "sour": 10,
            "salty": 0,
            "fruits": 10,
            "hoppy": 20,
            "spices": 5,
            "malty": 90,
        },
        {
            "full_name": "Brew B Mid",
            "name": "Mid",
            "brand": "Brew B",
            "category": "Stout",
            "abv": 5.0,
            "serving_ml": 375.0,
            "alcohol_ml": 375.0 * 5.0 / 100.0,
            "alcohol_grams": 375.0 * 5.0 / 100.0 * 0.789,
            "image_url": "",
            "recommendable": True,
            "astringency": 11,
            "body": 78,
            "bitter": 38,
            "sweet": 48,
            "sour": 12,
            "salty": 0,
            "fruits": 12,
            "hoppy": 22,
            "spices": 6,
            "malty": 88,
        },
        {
            "full_name": "Brew C Light",
            "name": "Light",
            "brand": "Brew C",
            "category": "Lager",
            "abv": 3.0,
            "serving_ml": 375.0,
            "alcohol_ml": 375.0 * 3.0 / 100.0,
            "alcohol_grams": 375.0 * 3.0 / 100.0 * 0.789,
            "image_url": "",
            "recommendable": True,
            "astringency": 5,
            "body": 20,
            "bitter": 10,
            "sweet": 20,
            "sour": 5,
            "salty": 0,
            "fruits": 5,
            "hoppy": 10,
            "spices": 0,
            "malty": 20,
        },
        {
            "full_name": "Brew D Broken",
            "name": "Broken",
            "brand": "Brew D",
            "category": "Ale",
            "abv": 4.0,
            "serving_ml": 375.0,
            "alcohol_ml": 15.0,
            "alcohol_grams": 11.835,
            "image_url": "",
            "recommendable": False,
            **{f: 0 for f in TASTE_FEATURES},
        },
    ]
    return pd.DataFrame(rows)


def test_taste_feature_schema_excludes_sensory_alcohol():
    assert "alcohol" not in TASTE_FEATURES
    assert "abv" not in TASTE_FEATURES


def test_recommend_lower_alcohol_and_no_self():
    model = SipMateRecommender().fit(_tiny_catalog())
    result = model.recommend("Brew A Heavy", top_k=2)
    assert result.reason is None
    assert result.recommendations
    keys = [r.product_key for r in result.recommendations]
    assert "Brew A Heavy" not in keys
    for rec in result.recommendations:
        assert rec.alcohol_ml < (375.0 * 8.0 / 100.0)
        assert rec.abv < 8.0


def test_similarity_prefers_taste_neighbour():
    model = SipMateRecommender().fit(_tiny_catalog())
    result = model.recommend("Brew A Heavy", top_k=1)
    assert result.recommendations[0].product_key == "Brew B Mid"


def test_no_candidates_for_lightest():
    model = SipMateRecommender().fit(_tiny_catalog())
    result = model.recommend("Brew C Light", top_k=3)
    assert result.recommendations == []
    assert result.reason == "NO_CANDIDATES"


def test_unknown_product():
    model = SipMateRecommender().fit(_tiny_catalog())
    result = model.recommend("Does Not Exist", top_k=3)
    assert result.reason == "PRODUCT_NOT_IN_MODEL"


def test_non_recommendable_excluded_from_fit():
    model = SipMateRecommender().fit(_tiny_catalog())
    assert model.n_products == 3
    assert "Brew D Broken" not in model.product_keys


def test_save_and_load_roundtrip(tmp_path: Path):
    model = SipMateRecommender().fit(_tiny_catalog())
    model.save(tmp_path)
    loaded = SipMateRecommender.load(tmp_path)
    a = model.recommend("Brew A Heavy", top_k=2).to_dict()
    b = loaded.recommend("Brew A Heavy", top_k=2).to_dict()
    assert a["recommendations"][0]["product_key"] == b["recommendations"][0]["product_key"]
