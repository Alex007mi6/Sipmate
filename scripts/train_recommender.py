"""
Train SipMate constraint-based KNN recommender from cleaned products.

Usage (repo root):
    py -3 scripts/train_recommender.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.recommender import SipMateRecommender  # noqa: E402

CLEANED = ROOT / "data" / "processed" / "products_cleaned.csv"
CLEAN_SUMMARY = ROOT / "data" / "processed" / "cleaning_summary.json"
MODELS_DIR = ROOT / "models"


def main() -> None:
    if not CLEANED.exists():
        raise FileNotFoundError(
            f"Missing cleaned dataset: {CLEANED}. Run scripts/clean_data.py first."
        )

    df = pd.read_csv(CLEANED)
    dataset_version = "unknown"
    if CLEAN_SUMMARY.exists():
        summary = json.loads(CLEAN_SUMMARY.read_text(encoding="utf-8"))
        dataset_version = summary.get(
            "generated_at_utc", df["dataset_version"].iloc[0] if "dataset_version" in df else "unknown"
        )
        if "dataset_version" in df.columns:
            dataset_version = str(df["dataset_version"].iloc[0])

    model = SipMateRecommender().fit(
        df,
        product_key_col="full_name",
        recommendable_col="recommendable",
        dataset_version=str(dataset_version),
    )
    paths = model.save(MODELS_DIR)

    # Smoke check on a mid-ABV product
    sample_key = df.loc[df["recommendable"] & (df["abv"] >= 5) & (df["abv"] <= 6), "full_name"]
    if not sample_key.empty:
        demo = model.recommend(str(sample_key.iloc[0]), top_k=3)
        print("Demo selected:", demo.selected_product_key)
        print("Demo reason:", demo.reason)
        for rec in demo.recommendations:
            print(
                f"  -> {rec.name} | ABV {rec.abv} | match {rec.taste_match_pct}% | "
                f"alc_ml ↓ {rec.alcohol_ml_reduction_pct}%"
            )

    print("Training complete")
    print(f"  products fitted: {model.n_products}")
    print(f"  features: {model.feature_names}")
    for name, path in paths.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
