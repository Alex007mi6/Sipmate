"""
SipMate reproducible data cleaning pipeline.

Reads immutable raw CSV from data/raw/, writes cleaned products to
data/processed/, and prints a summary. Never modifies raw files.

Usage (from repo root):
    py -3 scripts/clean_data.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "beer_profile_and_ratings.csv"
OUT_CSV = ROOT / "data" / "processed" / "products_cleaned.csv"
OUT_SUMMARY = ROOT / "data" / "processed" / "cleaning_summary.json"

# Sensory Alcohol is intentionally excluded from taste similarity (approved 2026-08-11).
TASTE_FEATURES = [
    "Astringency",
    "Body",
    "Bitter",
    "Sweet",
    "Sour",
    "Salty",
    "Fruits",
    "Hoppy",
    "Spices",
    "Malty",
]

# Extreme but real specialty beers exist; flag rather than delete by default.
ABV_OUTLIER_THRESHOLD = 20.0

# Source data has no serving size. Default stub serving for per-serving alcohol
# constraint; admins can override per product later in PostgreSQL.
DEFAULT_SERVING_ML = 375.0
ALCOHOL_DENSITY_G_PER_ML = 0.789


def alcohol_from_serving(abv: pd.Series, serving_ml: float) -> tuple[pd.Series, pd.Series]:
    """Return (alcohol_ml, alcohol_grams) from ABV% and serving volume."""
    alcohol_ml = serving_ml * abv / 100.0
    alcohol_grams = alcohol_ml * ALCOHOL_DENSITY_G_PER_ML
    return alcohol_ml, alcohol_grams


def clean_description(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).replace("\\t", " ").replace("\t", " ").strip()
    if text.lower().startswith("notes:"):
        text = text[6:].strip()
    return " ".join(text.split())


def run() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_PATH}")

    raw = pd.read_csv(RAW_PATH)
    n_raw = len(raw)

    exact_dupes = int(raw.duplicated().sum())
    name_dupes = int(raw["Name"].duplicated().sum())
    brewery_name_dupes = int(raw.duplicated(subset=["Brewery", "Name"]).sum())
    full_name_dupes = int(raw["Beer Name (Full)"].duplicated().sum())

    if full_name_dupes:
        raise ValueError(
            "Beer Name (Full) is not unique; cannot use it as natural key without merge rules."
        )

    df = raw.copy()
    df["name"] = df["Name"].astype(str).str.strip()
    df["full_name"] = df["Beer Name (Full)"].astype(str).str.strip()
    df["brand"] = df["Brewery"].astype(str).str.strip()
    df["category"] = df["Style"].astype(str).str.strip()
    df["description"] = df["Description"].map(clean_description)
    df["abv"] = pd.to_numeric(df["ABV"], errors="coerce")

    for col in TASTE_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Dataset has no native serving size — apply default stub; per-product editable later.
    df["serving_ml"] = float(DEFAULT_SERVING_ML)
    df["alcohol_ml"], df["alcohol_grams"] = alcohol_from_serving(
        df["abv"], DEFAULT_SERVING_ML
    )

    missing_abv = df["abv"].isna()
    abv_zero = df["abv"].fillna(-1).eq(0)
    # Styles at ABV 0 look like ordinary beers with missing values, not labelled AF products.
    abv_suspicious = abv_zero | missing_abv
    taste_missing = df[TASTE_FEATURES].isna().any(axis=1)
    taste_all_zero = df[TASTE_FEATURES].sum(axis=1).eq(0)
    missing_taste_profile = taste_missing | taste_all_zero
    abv_outlier = df["abv"].gt(ABV_OUTLIER_THRESHOLD)

    recommendable = ~(abv_suspicious | missing_taste_profile)

    out = pd.DataFrame(
        {
            "full_name": df["full_name"],
            "name": df["name"],
            "brand": df["brand"],
            "category": df["category"],
            "description": df["description"],
            "abv": df["abv"],
            "serving_ml": df["serving_ml"],
            "alcohol_ml": df["alcohol_ml"],
            "alcohol_grams": df["alcohol_grams"],
            "abv_suspicious": abv_suspicious.astype(bool),
            "missing_taste_profile": missing_taste_profile.astype(bool),
            "abv_outlier": abv_outlier.fillna(False).astype(bool),
            "recommendable": recommendable.astype(bool),
            "image_url": "",
            "source_dataset": "beer_profile_and_ratings.csv",
            "dataset_version": "raw-2026-08-11",
        }
    )

    for col in TASTE_FEATURES:
        out[col.lower()] = df[col]

    # Stable sort for reproducibility
    out = out.sort_values(["brand", "full_name"], kind="mergesort").reset_index(drop=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(RAW_PATH.relative_to(ROOT)).replace("\\", "/"),
        "output_path": str(OUT_CSV.relative_to(ROOT)).replace("\\", "/"),
        "n_raw_rows": n_raw,
        "n_cleaned_rows": int(len(out)),
        "n_recommendable": int(out["recommendable"].sum()),
        "n_excluded_from_recommendation": int((~out["recommendable"]).sum()),
        "duplicate_analysis": {
            "exact_row_duplicates": exact_dupes,
            "name_only_duplicates": name_dupes,
            "brewery_plus_name_duplicates": brewery_name_dupes,
            "full_name_duplicates": full_name_dupes,
            "action": (
                "Kept all rows. Short Name collisions are different brewery products. "
                "Natural key is full_name (Beer Name (Full))."
            ),
        },
        "missing_values": {
            "raw_null_counts": {c: int(raw[c].isna().sum()) for c in raw.columns},
            "taste_strategy": (
                "No NaNs in source taste columns. Rows with all taste features == 0 "
                "treated as missing profile and marked missing_taste_profile / not recommendable. "
                "Individual zeros (especially Salty) retained as valid sensory scores."
            ),
            "abv_strategy": (
                "ABV already numeric. ABV == 0 (or NaN after coercion) flagged abv_suspicious "
                "and excluded from recommendation until manually verified/corrected."
            ),
        },
        "abv": {
            "min": float(out["abv"].min()),
            "max": float(out["abv"].max()),
            "n_abv_suspicious": int(out["abv_suspicious"].sum()),
            "n_abv_outlier_gt_20": int(out["abv_outlier"].sum()),
            "outlier_threshold": ABV_OUTLIER_THRESHOLD,
            "outlier_action": "Flagged abv_outlier; kept recommendable if taste profile valid.",
        },
        "serving_size": {
            "present_in_source": False,
            "default_serving_ml": DEFAULT_SERVING_ML,
            "serving_ml_applied": DEFAULT_SERVING_ML,
            "alcohol_density_g_per_ml": ALCOHOL_DENSITY_G_PER_ML,
            "formula": "alcohol_ml = serving_ml * abv / 100; alcohol_grams = alcohol_ml * 0.789",
            "per_product_editable_later": True,
            "primary_constraint": "alcohol_ml",
            "fallback_constraint": "ABV (only if alcohol_ml missing)",
            "n_with_serving_ml": int(out["serving_ml"].notna().sum()),
            "n_with_alcohol_ml": int(out["alcohol_ml"].notna().sum()),
        },
        "taste_features_for_similarity": [c.lower() for c in TASTE_FEATURES],
        "excluded_from_similarity": [
            "alcohol (sensory mouthfeel column)",
            "abv",
            "min_ibu",
            "max_ibu",
            "review_*",
            "number_of_reviews",
        ],
        "decision_alcohol_sensory_excluded": True,
        "exclusions": {
            "n_missing_taste_profile": int(out["missing_taste_profile"].sum()),
            "n_abv_suspicious": int(out["abv_suspicious"].sum()),
        },
    }

    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("SipMate data cleaning complete")
    print(f"  raw rows:            {n_raw}")
    print(f"  cleaned rows:        {len(out)}")
    print(f"  recommendable:       {int(out['recommendable'].sum())}")
    print(f"  abv_suspicious:      {int(out['abv_suspicious'].sum())}")
    print(f"  missing_taste:       {int(out['missing_taste_profile'].sum())}")
    print(f"  abv_outlier (>20%):  {int(out['abv_outlier'].sum())}")
    print(f"  default serving_ml:  {DEFAULT_SERVING_ML}")
    print(f"  wrote: {OUT_CSV}")
    print(f"  wrote: {OUT_SUMMARY}")
    return out


if __name__ == "__main__":
    run()
