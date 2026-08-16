"""
Constraint-based taste recommender.

KNN identifies nearest neighbours; cosine distance is the similarity metric.
Candidates must have strictly lower alcohol per serving (alcohol_ml), with ABV
fallback only when alcohol_ml is missing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_distances
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from app.recommender.features import DEFAULT_TOP_K, TASTE_FEATURES


@dataclass(frozen=True)
class Recommendation:
    product_key: str
    name: str
    brand: str
    category: str
    abv: float
    serving_ml: float | None
    alcohol_ml: float | None
    alcohol_grams: float | None
    cosine_distance: float
    taste_match_pct: float
    abv_reduction: float
    abv_reduction_pct: float
    alcohol_ml_reduction: float | None
    alcohol_ml_reduction_pct: float | None
    image_url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_key": self.product_key,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "abv": self.abv,
            "serving_ml": self.serving_ml,
            "alcohol_ml": self.alcohol_ml,
            "alcohol_grams": self.alcohol_grams,
            "cosine_distance": round(float(self.cosine_distance), 6),
            "taste_match_pct": round(float(self.taste_match_pct), 1),
            "abv_reduction": round(float(self.abv_reduction), 3),
            "abv_reduction_pct": round(float(self.abv_reduction_pct), 1),
            "alcohol_ml_reduction": (
                None
                if self.alcohol_ml_reduction is None
                else round(float(self.alcohol_ml_reduction), 3)
            ),
            "alcohol_ml_reduction_pct": (
                None
                if self.alcohol_ml_reduction_pct is None
                else round(float(self.alcohol_ml_reduction_pct), 1)
            ),
            "image_url": self.image_url,
        }


@dataclass(frozen=True)
class RecommendationResult:
    selected_product_key: str
    recommendations: list[Recommendation]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_product_key": self.selected_product_key,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "reason": self.reason,
        }


def _taste_match_pct(cosine_distance: float) -> float:
    # cosine distance in [0, 2] for sklearn; clamp display to [0, 100]
    sim = 1.0 - float(cosine_distance)
    return float(np.clip(sim * 100.0, 0.0, 100.0))


def _as_optional_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class SipMateRecommender:
    """Fit/load offline artifacts and serve constrained recommendations."""

    def __init__(self) -> None:
        self.feature_names: list[str] = list(TASTE_FEATURES)
        self.scaler: StandardScaler | None = None
        self.nn: NearestNeighbors | None = None
        self.X: np.ndarray | None = None  # scaled feature matrix
        self.product_keys: list[str] = []
        self.meta_df: pd.DataFrame | None = None
        self.key_to_index: dict[str, int] = {}
        self.metadata: dict[str, Any] = {}

    @property
    def n_products(self) -> int:
        return 0 if self.X is None else int(self.X.shape[0])

    def fit(
        self,
        products: pd.DataFrame,
        *,
        product_key_col: str = "full_name",
        recommendable_col: str = "recommendable",
        dataset_version: str = "unknown",
        default_top_k: int = DEFAULT_TOP_K,
    ) -> "SipMateRecommender":
        df = products.copy()
        if recommendable_col in df.columns:
            df = df[df[recommendable_col].astype(bool)].copy()

        missing = [c for c in self.feature_names if c not in df.columns]
        if missing:
            raise ValueError(f"Missing taste feature columns: {missing}")
        if product_key_col not in df.columns:
            raise ValueError(f"Missing product key column: {product_key_col}")
        if "abv" not in df.columns:
            raise ValueError("Missing abv column")

        df = df.reset_index(drop=True)
        if df.empty:
            raise ValueError("No recommendable products to fit")

        if df[product_key_col].duplicated().any():
            raise ValueError(f"{product_key_col} must be unique in training set")

        raw_X = df[self.feature_names].astype(float).to_numpy()
        if np.isnan(raw_X).any():
            raise ValueError("Taste features contain NaN after recommendable filter")

        self.scaler = StandardScaler()
        self.X = self.scaler.fit_transform(raw_X)

        # Fitted for reproducibility / paper narrative; constrained serve uses
        # explicit candidate filtering + cosine distance ranking.
        self.nn = NearestNeighbors(metric="cosine", algorithm="brute")
        self.nn.fit(self.X)

        meta_cols = [
            product_key_col,
            "name",
            "brand",
            "category",
            "abv",
            "serving_ml",
            "alcohol_ml",
            "alcohol_grams",
            "image_url",
        ]
        for col in meta_cols:
            if col not in df.columns:
                df[col] = np.nan if col != "image_url" else ""

        self.meta_df = df[meta_cols].rename(columns={product_key_col: "product_key"})
        self.product_keys = self.meta_df["product_key"].astype(str).tolist()
        self.key_to_index = {k: i for i, k in enumerate(self.product_keys)}

        self.metadata = {
            "algorithm": "NearestNeighbors",
            "metric": "cosine",
            "sklearn_neighbors_note": (
                "KNN finds nearest neighbours; cosine distance is the similarity metric."
            ),
            "feature_names": list(self.feature_names),
            "excludes_sensory_alcohol": True,
            "scaler": "StandardScaler",
            "default_top_k": int(default_top_k),
            "dataset_version": dataset_version,
            "n_products": self.n_products,
            "constraint_primary": "alcohol_ml",
            "constraint_fallback": "abv",
            "product_key_col": product_key_col,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "random_state": None,
        }
        return self

    def _resolve_index(self, product_key: str) -> int | None:
        return self.key_to_index.get(str(product_key))

    def _candidate_mask(self, selected_idx: int) -> np.ndarray:
        assert self.meta_df is not None
        selected = self.meta_df.iloc[selected_idx]
        selected_alc = _as_optional_float(selected["alcohol_ml"])
        selected_abv = float(selected["abv"])

        mask = np.ones(self.n_products, dtype=bool)
        mask[selected_idx] = False

        if selected_alc is not None:
            cand_alc = self.meta_df["alcohol_ml"].to_numpy(dtype=float)
            # NaN candidates cannot satisfy alcohol_ml constraint → exclude
            mask &= np.isfinite(cand_alc) & (cand_alc < selected_alc)
        else:
            cand_abv = self.meta_df["abv"].to_numpy(dtype=float)
            mask &= np.isfinite(cand_abv) & (cand_abv < selected_abv)
        return mask

    def recommend(
        self,
        product_key: str,
        *,
        top_k: int = DEFAULT_TOP_K,
    ) -> RecommendationResult:
        if self.X is None or self.meta_df is None or self.scaler is None:
            return RecommendationResult(
                selected_product_key=str(product_key),
                recommendations=[],
                reason="MODEL_UNAVAILABLE",
            )

        idx = self._resolve_index(product_key)
        if idx is None:
            return RecommendationResult(
                selected_product_key=str(product_key),
                recommendations=[],
                reason="PRODUCT_NOT_IN_MODEL",
            )

        selected = self.meta_df.iloc[idx]
        if _as_optional_float(selected.get("alcohol_ml")) is None and (
            selected["abv"] is None or (isinstance(selected["abv"], float) and np.isnan(selected["abv"]))
        ):
            return RecommendationResult(
                selected_product_key=str(product_key),
                recommendations=[],
                reason="MISSING_FEATURES",
            )

        mask = self._candidate_mask(idx)
        if not mask.any():
            return RecommendationResult(
                selected_product_key=str(product_key),
                recommendations=[],
                reason="NO_CANDIDATES",
            )

        cand_indices = np.flatnonzero(mask)
        dists = cosine_distances(self.X[idx].reshape(1, -1), self.X[cand_indices])[0]
        order = np.argsort(dists)[: max(int(top_k), 0)]

        selected_abv = float(selected["abv"])
        selected_alc = _as_optional_float(selected["alcohol_ml"])
        recs: list[Recommendation] = []
        for rank_i in order:
            j = int(cand_indices[rank_i])
            row = self.meta_df.iloc[j]
            dist = float(dists[rank_i])
            cand_abv = float(row["abv"])
            cand_alc = _as_optional_float(row["alcohol_ml"])
            abv_reduction = selected_abv - cand_abv
            abv_reduction_pct = (
                (abv_reduction / selected_abv * 100.0) if selected_abv > 0 else 0.0
            )
            if selected_alc is not None and cand_alc is not None:
                alc_reduction = selected_alc - cand_alc
                alc_reduction_pct = (
                    (alc_reduction / selected_alc * 100.0) if selected_alc > 0 else 0.0
                )
            else:
                alc_reduction = None
                alc_reduction_pct = None

            recs.append(
                Recommendation(
                    product_key=str(row["product_key"]),
                    name=str(row["name"]),
                    brand=str(row["brand"]),
                    category=str(row["category"]),
                    abv=cand_abv,
                    serving_ml=_as_optional_float(row["serving_ml"]),
                    alcohol_ml=cand_alc,
                    alcohol_grams=_as_optional_float(row["alcohol_grams"]),
                    cosine_distance=dist,
                    taste_match_pct=_taste_match_pct(dist),
                    abv_reduction=abv_reduction,
                    abv_reduction_pct=abv_reduction_pct,
                    alcohol_ml_reduction=alc_reduction,
                    alcohol_ml_reduction_pct=alc_reduction_pct,
                    image_url="" if pd.isna(row["image_url"]) else str(row["image_url"]),
                )
            )

        return RecommendationResult(
            selected_product_key=str(product_key),
            recommendations=recs,
            reason=None,
        )

    def build_lighter_ladder(
        self,
        product_key: str,
        *,
        max_steps: int = 5,
        include_alcohol_free_target: bool = True,
        alcohol_free_abv_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Build a successive lighter path by repeatedly taking the top constrained
        recommendation from the current drink (no forced continuous ABV grid).
        """
        if self.meta_df is None:
            return []

        idx = self._resolve_index(product_key)
        if idx is None:
            return []

        start = self.meta_df.iloc[idx]
        ladder: list[dict[str, Any]] = [
            {
                "step": 0,
                "label": "Current",
                "product_key": str(start["product_key"]),
                "name": str(start["name"]),
                "abv": float(start["abv"]),
                "alcohol_ml": _as_optional_float(start["alcohol_ml"]),
                "taste_match_pct": 100.0,
            }
        ]

        current_key = str(product_key)
        seen = {current_key}
        for step in range(1, max_steps + 1):
            result = self.recommend(current_key, top_k=1)
            if not result.recommendations:
                break
            nxt = result.recommendations[0]
            if nxt.product_key in seen:
                break
            seen.add(nxt.product_key)
            ladder.append(
                {
                    "step": step,
                    "label": f"Lighter Step {step}",
                    "product_key": nxt.product_key,
                    "name": nxt.name,
                    "abv": nxt.abv,
                    "alcohol_ml": nxt.alcohol_ml,
                    "taste_match_pct": nxt.taste_match_pct,
                }
            )
            current_key = nxt.product_key
            if include_alcohol_free_target and nxt.abv <= alcohol_free_abv_threshold:
                ladder[-1]["label"] = "Alcohol-Free"
                break

        return ladder

    def save(self, models_dir: Path | str) -> dict[str, str]:
        if self.scaler is None or self.nn is None or self.X is None or self.meta_df is None:
            raise RuntimeError("Cannot save an unfitted recommender")

        models_dir = Path(models_dir)
        models_dir.mkdir(parents=True, exist_ok=True)

        scaler_path = models_dir / "scaler.joblib"
        recommender_path = models_dir / "recommender.joblib"
        matrix_path = models_dir / "feature_matrix.joblib"
        products_path = models_dir / "recommender_products.joblib"
        metadata_path = models_dir / "model_metadata.json"

        joblib.dump(self.scaler, scaler_path)
        joblib.dump(self.nn, recommender_path)
        joblib.dump(
            {
                "X": self.X,
                "feature_names": self.feature_names,
                "product_keys": self.product_keys,
            },
            matrix_path,
        )
        joblib.dump(self.meta_df, products_path)

        meta = dict(self.metadata)
        meta["artifact_paths"] = {
            "scaler": scaler_path.name,
            "recommender": recommender_path.name,
            "feature_matrix": matrix_path.name,
            "products": products_path.name,
            "metadata": metadata_path.name,
        }
        metadata_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self.metadata = meta

        return {k: str(models_dir / v) for k, v in meta["artifact_paths"].items()}

    @classmethod
    def load(cls, models_dir: Path | str) -> "SipMateRecommender":
        models_dir = Path(models_dir)
        metadata_path = models_dir / "model_metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Missing metadata: {metadata_path}")

        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        paths = meta.get("artifact_paths", {})

        obj = cls()
        obj.metadata = meta
        obj.feature_names = list(meta.get("feature_names", TASTE_FEATURES))
        obj.scaler = joblib.load(models_dir / paths.get("scaler", "scaler.joblib"))
        obj.nn = joblib.load(models_dir / paths.get("recommender", "recommender.joblib"))
        matrix_blob = joblib.load(
            models_dir / paths.get("feature_matrix", "feature_matrix.joblib")
        )
        obj.X = matrix_blob["X"]
        obj.product_keys = list(matrix_blob["product_keys"])
        obj.key_to_index = {k: i for i, k in enumerate(obj.product_keys)}
        obj.meta_df = joblib.load(
            models_dir / paths.get("products", "recommender_products.joblib")
        )
        return obj
