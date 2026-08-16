"""Taste feature schema for SipMate recommender."""

from __future__ import annotations

# Locked decision: sensory "Alcohol" column is excluded from similarity.
TASTE_FEATURES: list[str] = [
    "astringency",
    "body",
    "bitter",
    "sweet",
    "sour",
    "salty",
    "fruits",
    "hoppy",
    "spices",
    "malty",
]

DEFAULT_TOP_K = 3
ALCOHOL_DENSITY_G_PER_ML = 0.789
