"""SipMate recommendation package (constraint-based KNN + cosine distance)."""

from app.recommender.engine import SipMateRecommender
from app.recommender.features import TASTE_FEATURES, DEFAULT_TOP_K

__all__ = ["SipMateRecommender", "TASTE_FEATURES", "DEFAULT_TOP_K"]
