"""Recommendation model version management."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelVersion, Product
from app.models.base import ModelStatus
from app.recommender import SipMateRecommender
from app.services import recommendation_service

logger = logging.getLogger("sipmate.model")

ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT / "models"


def get_active_model_version(db: Session) -> ModelVersion | None:
    return db.scalar(
        select(ModelVersion)
        .where(ModelVersion.status == ModelStatus.active)
        .order_by(ModelVersion.id.desc())
    )


def mark_model_stale(db: Session) -> None:
    active = get_active_model_version(db)
    if active is not None and active.status == ModelStatus.active:
        active.status = ModelStatus.stale
        db.flush()


def get_model_status(db: Session) -> dict:
    active = get_active_model_version(db)
    loaded = recommendation_service.load_recommender()
    stale = active is not None and active.status == ModelStatus.stale
    return {
        "loaded": loaded is not None,
        "n_products": loaded.n_products if loaded else None,
        "active_version_id": active.id if active else None,
        "active_version_status": active.status.value if active else None,
        "stale": stale,
        "product_count": active.product_count if active else None,
        "created_at": active.created_at if active else None,
        "activated_at": active.activated_at if active else None,
    }


def rebuild_model(db: Session, *, models_dir: Path | None = None) -> ModelVersion:
    target_dir = models_dir or MODELS_DIR
    products = list(
        db.scalars(
            select(Product).where(
                Product.is_active.is_(True),
                Product.recommendable.is_(True),
            )
        ).all()
    )
    if not products:
        raise ValueError("No active recommendable products to rebuild model.")

    rows = []
    for p in products:
        row = {
            "full_name": p.full_name,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "abv": p.abv,
            "serving_ml": p.serving_ml,
            "alcohol_ml": p.alcohol_ml,
            "alcohol_grams": p.alcohol_grams,
            "image_url": p.image_url or "",
            "recommendable": True,
        }
        row.update(p.taste_features or {})
        rows.append(row)

    df = pd.DataFrame(rows)
    model = SipMateRecommender().fit(df, dataset_version="db-rebuild")
    paths = model.save(target_dir)

    now = datetime.now(timezone.utc)
    for prev in db.scalars(
        select(ModelVersion).where(ModelVersion.status == ModelStatus.active)
    ).all():
        prev.status = ModelStatus.archived

    version = ModelVersion(
        algorithm=str(model.metadata.get("algorithm", "NearestNeighbors")),
        feature_names=list(model.feature_names),
        dataset_version=str(model.metadata.get("dataset_version", "db-rebuild")),
        model_path=paths.get("recommender", str(target_dir / "recommender.joblib")),
        scaler_path=paths.get("scaler", str(target_dir / "scaler.joblib")),
        metadata_path=paths.get("metadata", str(target_dir / "model_metadata.json")),
        status=ModelStatus.active,
        product_count=model.n_products,
        notes="Admin rebuild from active DB products",
        created_at=now,
        activated_at=now,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    recommendation_service.MODELS_DIR = target_dir
    recommendation_service.reload_recommender()
    logger.info("Model rebuilt version=%s products=%s", version.id, version.product_count)
    return version
