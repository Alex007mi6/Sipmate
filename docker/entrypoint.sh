#!/bin/sh
set -e
cd /app

# Idempotent schema migrate before serving traffic
alembic upgrade head

PORT="${PORT:-8000}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
