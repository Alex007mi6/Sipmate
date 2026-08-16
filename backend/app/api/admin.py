"""Admin routes: products, rewards, redemptions, model management."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.core.db import get_db
from app.core.errors import raise_error
from app.models import Product, Redemption, Reward, User
from app.models.base import RedemptionStatus
from app.schemas.admin import (
    AdminProductListOut,
    AdminRedemptionOut,
    ImageUploadOut,
    ModelRebuildOut,
    ModelStatusOut,
    ProductCreateIn,
    ProductUpdateIn,
)
from app.schemas.products import ProductOut
from app.schemas.rewards import RewardCreateIn, RewardOut, RewardUpdateIn
from app.services import model_service, product_service
from app.storage.local import LocalStorageService

router = APIRouter(prefix="/admin", tags=["admin"])

STALE_FIELDS = frozenset(
    {"abv", "serving_ml", "alcohol_ml", "alcohol_grams", "taste_features", "is_active", "recommendable"}
)


def _product_changed_for_model(body: ProductUpdateIn) -> bool:
    data = body.model_dump(exclude_unset=True)
    return bool(STALE_FIELDS.intersection(data.keys()))


@router.get("/products", response_model=AdminProductListOut)
def admin_list_products(
    q: str | None = None,
    category: str | None = None,
    active_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProductListOut:
    items, total = product_service.list_products(
        db,
        q=q,
        category=category,
        recommendable_only=False,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    return AdminProductListOut(
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/products", response_model=ProductOut, status_code=201)
def admin_create_product(
    body: ProductCreateIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = Product(**body.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_error(409, "PRODUCT_EXISTS", "A product with this full_name already exists.")
    db.refresh(product)
    model_service.mark_model_stale(db)
    db.commit()
    return ProductOut.model_validate(product)


@router.get("/products/{product_id}", response_model=ProductOut)
def admin_get_product(
    product_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")
    return ProductOut.model_validate(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
def admin_update_product(
    product_id: int,
    body: ProductUpdateIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")

    mark_stale = _product_changed_for_model(body)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(product, key, value)

    if "abv" in updates or "serving_ml" in updates:
        serving = product.serving_ml
        if serving is not None and product.abv is not None:
            product.alcohol_ml = float(serving) * float(product.abv) / 100.0
            product.alcohol_grams = product.alcohol_ml * 0.789

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_error(409, "PRODUCT_CONFLICT", "Product update conflict.")
    db.refresh(product)

    if mark_stale:
        model_service.mark_model_stale(db)
        db.commit()

    return ProductOut.model_validate(product)


@router.delete("/products/{product_id}", response_model=ProductOut)
def admin_delete_product(
    product_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")
    product.is_active = False
    model_service.mark_model_stale(db)
    db.commit()
    db.refresh(product)
    return ProductOut.model_validate(product)


@router.post("/products/{product_id}/image", response_model=ImageUploadOut)
async def admin_upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImageUploadOut:
    product = product_service.get_product(db, product_id)
    if product is None:
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")

    content_type = file.content_type or "application/octet-stream"
    storage = LocalStorageService()
    url, key = storage.save(
        file=file.file,
        filename=file.filename or "upload",
        content_type=content_type,
        prefix=f"products/{product_id}/",
    )
    if product.image_key:
        storage.delete(product.image_key)
    product.image_url = url
    product.image_key = key
    db.commit()
    return ImageUploadOut(image_url=url, image_key=key)


@router.get("/rewards", response_model=list[RewardOut])
def admin_list_rewards(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[RewardOut]:
    rewards = list(db.scalars(select(Reward).order_by(Reward.name)).all())
    return [RewardOut.model_validate(r) for r in rewards]


@router.post("/rewards", response_model=RewardOut, status_code=201)
def admin_create_reward(
    body: RewardCreateIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RewardOut:
    reward = Reward(**body.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return RewardOut.model_validate(reward)


@router.patch("/rewards/{reward_id}", response_model=RewardOut)
def admin_update_reward(
    reward_id: int,
    body: RewardUpdateIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RewardOut:
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise_error(404, "REWARD_NOT_FOUND", "Reward not found.")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(reward, key, value)
    db.commit()
    db.refresh(reward)
    return RewardOut.model_validate(reward)


@router.delete("/rewards/{reward_id}", response_model=RewardOut)
def admin_delete_reward(
    reward_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RewardOut:
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise_error(404, "REWARD_NOT_FOUND", "Reward not found.")
    reward.active = False
    db.commit()
    db.refresh(reward)
    return RewardOut.model_validate(reward)


@router.get("/redemptions", response_model=list[AdminRedemptionOut])
def admin_list_redemptions(
    status: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminRedemptionOut]:
    stmt = (
        select(Redemption, Reward, User)
        .join(Reward, Reward.id == Redemption.reward_id)
        .join(User, User.id == Redemption.user_id)
        .order_by(Redemption.created_at.desc())
    )
    if status:
        try:
            st = RedemptionStatus(status)
        except ValueError:
            raise_error(400, "INVALID_STATUS", f"Invalid status: {status}")
        stmt = stmt.where(Redemption.status == st)

    rows = db.execute(stmt).all()
    return [
        AdminRedemptionOut(
            id=r.id,
            user_id=u.id,
            user_email=u.email,
            reward_id=rw.id,
            reward_name=rw.name,
            points_spent=r.points_spent,
            redemption_code=r.redemption_code,
            status=r.status.value,
            created_at=r.created_at,
            redeemed_at=r.redeemed_at,
        )
        for r, rw, u in rows
    ]


@router.post("/redemptions/{code}/confirm", response_model=AdminRedemptionOut)
def admin_confirm_redemption(
    code: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminRedemptionOut:
    redemption = db.scalar(select(Redemption).where(Redemption.redemption_code == code.upper()))
    if redemption is None:
        raise_error(404, "REDEMPTION_NOT_FOUND", "Redemption code not found.")
    if redemption.status != RedemptionStatus.pending:
        raise_error(409, "ALREADY_PROCESSED", "Redemption has already been processed.")

    redemption.status = RedemptionStatus.redeemed
    redemption.redeemed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(redemption)

    reward = db.get(Reward, redemption.reward_id)
    user = db.get(User, redemption.user_id)
    return AdminRedemptionOut(
        id=redemption.id,
        user_id=redemption.user_id,
        user_email=user.email if user else "",
        reward_id=redemption.reward_id,
        reward_name=reward.name if reward else "",
        points_spent=redemption.points_spent,
        redemption_code=redemption.redemption_code,
        status=redemption.status.value,
        created_at=redemption.created_at,
        redeemed_at=redemption.redeemed_at,
    )


@router.get("/model/status", response_model=ModelStatusOut)
def admin_model_status(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ModelStatusOut:
    return ModelStatusOut(**model_service.get_model_status(db))


@router.post("/model/rebuild", response_model=ModelRebuildOut)
def admin_model_rebuild(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ModelRebuildOut:
    try:
        version = model_service.rebuild_model(db)
    except ValueError as exc:
        raise_error(422, "REBUILD_FAILED", str(exc))
    except Exception:
        raise_error(500, "REBUILD_FAILED", "Model rebuild failed.")
    return ModelRebuildOut(
        ok=True,
        version_id=version.id,
        product_count=version.product_count,
        message="Model rebuilt successfully.",
    )
