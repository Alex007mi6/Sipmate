# SipMate

Mobile-first web prototype for **responsible lighter-drink recommendations** in pub contexts.

Thesis focus: constraint-based KNN (cosine distance) over taste features, plus light gamification for accepting lower-alcohol alternatives.

## Architecture

```text
React (Vite)  →  FastAPI  →  PostgreSQL
                     ↓
              joblib KNN model + local/object storage
```

- Guests can browse, recommend, and view Lighter Ladder without login.
- Login unlocks points ledger, badges, and reward redemptions.
- Admin manages products, rewards, redemption codes, and model rebuild.

## Requirements

- Python 3.11+ (3.12 recommended for deploy images; 3.14 used in local Windows setup)
- Node.js 20+
- PostgreSQL 16 (production / Docker). Local smoke testing can use SQLite via `DATABASE_URL`.

## Environment Variables

Copy `.env.example` to `.env` and edit. Important keys:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://...`) |
| `SECRET_KEY` | JWT signing secret |
| `COOKIE_SECURE` | `true` in production HTTPS |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seeded admin account |
| `STORAGE_BACKEND` | `local` (default) |
| `LOCAL_UPLOAD_DIR` | Upload directory |

## Installation

```bash
# Python deps
py -3 -m pip install -r requirements.txt

# Frontend deps
cd frontend && npm install && cd ..
```

## Database Setup

```bash
# With PostgreSQL running (Docker Compose db service recommended):
alembic upgrade head

# Temporary local SQLite smoke test (not for production):
# set DATABASE_URL=sqlite:///./sipmate_dev.db
# then create tables with Base.metadata.create_all or use import after create_all
```

## Dataset

- Raw files live under `Beer Dataset/` and are mirrored to `data/raw/` (do not mutate raw).
- Primary table: `beer_profile_and_ratings.csv`.

## Data Cleaning

```bash
py -3 scripts/clean_data.py
```

Outputs: `data/processed/products_cleaned.csv`, cleaning summary JSON, updates reports.

Default `serving_ml = 375` (editable later per product). Sensory `Alcohol` column is excluded from taste similarity.

## Product Import

```bash
py -3 scripts/import_products.py
```

Idempotent upsert by `full_name`.

## Model Training

```bash
py -3 scripts/train_recommender.py
```

Writes `models/scaler.joblib`, `recommender.joblib`, `model_metadata.json`, etc.

## Offline Evaluation

```bash
py -3 scripts/evaluate_recommender.py
```

Writes `reports/offline_evaluation.md` and `.json`.

## Seed Admin / Badges / Rewards

```bash
py -3 scripts/seed.py
```

## Backend

```bash
# from repo root
$env:PYTHONPATH="backend"   # PowerShell
py -3 -m uvicorn app.main:app --reload --app-dir backend --port 8000
```

Health: `GET /health`

## Frontend

```bash
cd frontend
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

## Tests

```bash
py -3 -m pytest backend/tests -q
cd frontend && npm run build
```

## Docker

```bash
docker compose up --build
```

Provides PostgreSQL + API. Frontend can be served separately via `npm run build` and a static host, or proxied in a later production image.

**Note:** Docker CLI was not available on the original authoring machine; compose files are still provided.

## Admin

1. Run `scripts/seed.py`
2. Log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. Open `/admin` for products, rewards, redemption confirm, model rebuild

## Deployment

Recommended simple stack for a thesis prototype:

1. Managed PostgreSQL (Neon / Supabase)
2. Render or Railway web service for FastAPI (+ built frontend static files or separate static host)
3. Local/Cloudinary/S3 for images
4. Set `COOKIE_SECURE=true`, strong `SECRET_KEY`, HTTPS, run `alembic upgrade head`, import products, train/rebuild model

This environment did **not** contain hosting credentials. Deployment configs are prepared; actual public deploy requires your platform login and secrets.

## Project Layout

See `docs/sipmate-system-design.md` for full design. Key folders: `frontend/`, `backend/`, `data/`, `models/`, `scripts/`, `reports/`, `alembic/`, `docker/`.
