from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import raise_error
from app.schemas.products import ProductListOut, ProductOut
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListOut)
def get_products(
    q: str | None = None,
    category: str | None = None,
    recommendable_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ProductListOut:
    items, total = product_service.list_products(
        db,
        q=q,
        category=category,
        recommendable_only=recommendable_only,
        limit=limit,
        offset=offset,
    )
    return ProductListOut(
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/categories", response_model=list[str])
def get_categories(db: Session = Depends(get_db)) -> list[str]:
    return product_service.list_categories(db)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductOut:
    product = product_service.get_product(db, product_id)
    if product is None or not product.is_active:
        raise_error(404, "PRODUCT_NOT_FOUND", "Product not found.")
    return ProductOut.model_validate(product)
