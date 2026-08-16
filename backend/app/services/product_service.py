"""Product query service."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Product


def list_products(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    recommendable_only: bool = False,
    active_only: bool = True,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Product], int]:
    stmt = select(Product)
    count_stmt = select(func.count()).select_from(Product)

    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
        count_stmt = count_stmt.where(Product.is_active.is_(True))
    if recommendable_only:
        stmt = stmt.where(Product.recommendable.is_(True))
        count_stmt = count_stmt.where(Product.recommendable.is_(True))
    if category:
        stmt = stmt.where(Product.category == category)
        count_stmt = count_stmt.where(Product.category == category)
    if q:
        like = f"%{q.strip()}%"
        filt = or_(
            Product.name.ilike(like),
            Product.brand.ilike(like),
            Product.full_name.ilike(like),
            Product.category.ilike(like),
        )
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)

    total = int(db.scalar(count_stmt) or 0)
    items = list(
        db.scalars(stmt.order_by(Product.brand, Product.name).limit(limit).offset(offset)).all()
    )
    return items, total


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def list_categories(db: Session, *, active_only: bool = True) -> list[str]:
    stmt = select(Product.category).distinct().order_by(Product.category)
    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    return [c for c in db.scalars(stmt).all() if c]
