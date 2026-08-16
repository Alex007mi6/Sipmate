#!/bin/sh
set -e
cd /app

# Idempotent schema migrate before serving traffic
alembic upgrade head

# First-boot seed + product import (free tier has no preDeployCommand).
# Scripts are idempotent; import runs only when the products table is empty.
if [ "${AUTO_BOOTSTRAP:-true}" = "true" ]; then
  PYTHONPATH=/app/backend python scripts/seed.py
  COUNT=$(PYTHONPATH=/app/backend python -c "from sqlalchemy import func, select; from app.core.db import SessionLocal; from app.models import Product; db=SessionLocal(); print(db.scalar(select(func.count()).select_from(Product)) or 0); db.close()")
  if [ "$COUNT" = "0" ]; then
    echo "Bootstrapping products (empty DB)..."
    PYTHONPATH=/app/backend python scripts/import_products.py
  else
    echo "Products already present ($COUNT); skip import."
  fi
fi

PORT="${PORT:-8000}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
