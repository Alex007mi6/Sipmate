"""
Import cleaned products into the database (idempotent upsert by full_name).

Usage (repo root):
    py -3 scripts/import_products.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.db import SessionLocal  # noqa: E402
from app.models import Product  # noqa: E402
from app.recommender.features import TASTE_FEATURES  # noqa: E402

CLEANED = ROOT / "data" / "processed" / "products_cleaned.csv"
ALCOHOL_DENSITY = 0.789


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float_or_none(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def row_to_fields(row: pd.Series) -> dict:
    abv = float(row["abv"])
    serving_ml = _float_or_none(row.get("serving_ml"))
    alcohol_ml = _float_or_none(row.get("alcohol_ml"))
    alcohol_grams = _float_or_none(row.get("alcohol_grams"))

    if serving_ml is not None and alcohol_ml is None and pd.notna(abv):
        alcohol_ml = serving_ml * abv / 100.0
    if alcohol_ml is not None and alcohol_grams is None:
        alcohol_grams = alcohol_ml * ALCOHOL_DENSITY

    taste = {feat: float(row[feat]) for feat in TASTE_FEATURES}
    image_url = row.get("image_url")
    if image_url is None or (isinstance(image_url, float) and pd.isna(image_url)):
        image_url = None
    else:
        image_url = str(image_url).strip() or None

    recommendable = _bool(row.get("recommendable", True))
    abv_suspicious = _bool(row.get("abv_suspicious", False))
    missing_taste = _bool(row.get("missing_taste_profile", False))

    return {
        "name": str(row["name"]).strip(),
        "full_name": str(row["full_name"]).strip(),
        "brand": str(row["brand"]).strip(),
        "category": str(row["category"]).strip(),
        "description": "" if pd.isna(row.get("description")) else str(row.get("description")),
        "abv": abv,
        "serving_ml": serving_ml,
        "alcohol_ml": alcohol_ml,
        "alcohol_grams": alcohol_grams,
        "taste_features": taste,
        "image_url": image_url,
        "abv_suspicious": abv_suspicious,
        "missing_taste_profile": missing_taste,
        "recommendable": recommendable and not abv_suspicious and not missing_taste,
        "is_active": True,
    }


def import_products(db: Session, csv_path: Path) -> dict[str, int]:
    df = pd.read_csv(csv_path)
    created = updated = skipped = 0

    existing = {
        p.full_name: p
        for p in db.scalars(select(Product)).all()
    }

    for _, row in df.iterrows():
        fields = row_to_fields(row)
        full_name = fields["full_name"]
        current = existing.get(full_name)
        if current is None:
            product = Product(**fields)
            db.add(product)
            existing[full_name] = product
            created += 1
            continue

        changed = False
        for key, value in fields.items():
            if getattr(current, key) != value:
                setattr(current, key, value)
                changed = True
        if changed:
            updated += 1
        else:
            skipped += 1

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "total_csv": len(df)}


def main() -> None:
    if not CLEANED.exists():
        raise FileNotFoundError(f"Missing cleaned CSV: {CLEANED}")

    db = SessionLocal()
    try:
        stats = import_products(db, CLEANED)
    finally:
        db.close()

    print("Product import complete")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
