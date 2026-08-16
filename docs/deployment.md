# Deployment (SipMate) — free Neon/Render path

## Status

Deploy configs are ready (`render.yaml`, Docker multi-stage with SPA, Neon-compatible `DATABASE_URL`).

A **public URL is not live yet** until you connect a Git host + free cloud accounts (this machine has no Render/Neon/GitHub CLI login).

## Recommended free stack

| Piece | Free option | Role |
|-------|-------------|------|
| Open-source DB | **PostgreSQL** on [Neon](https://neon.tech) *or* Render Postgres | Product / points data |
| App host | [Render](https://render.com) free Web Service (Docker) | FastAPI + built frontend |

Alternative: Render Blueprint uses **Render Postgres** only (no Neon account).

## Path A — Render Blueprint (fewest accounts)

1. Create a **GitHub** repo and push this project (needs `git init` + remote).
2. Sign up at [render.com](https://render.com) with GitHub.
3. **New → Blueprint** → select the repo (reads `render.yaml`).
4. After deploy, open the service **Shell** and run:

```bash
alembic upgrade head
PYTHONPATH=backend python scripts/seed.py
PYTHONPATH=backend python scripts/import_products.py
# models/ already in image if committed; else:
PYTHONPATH=backend python scripts/train_recommender.py
```

5. Set `CORS_ORIGINS` to your real `https://….onrender.com` URL (Blueprint placeholder may differ).
6. Open `/health` then the site root.

Free tier spins down after idle; first request may take ~30–60s.

## Path B — Neon Postgres + Render Web

1. Neon → create project → copy connection string (`postgresql://…`).
2. Render → New Web Service → Docker → this repo.
3. Env:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Neon URL (app auto-upgrades to `postgresql+psycopg://`) |
| `SECRET_KEY` | long random |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` (if frontend ever on another domain; same-origin can use `lax`) |
| `CORS_ORIGINS` | your Render URL |
| `ENVIRONMENT` | `production` |
| `FRONTEND_DIST` | `frontend/dist` |

4. Same migrate / seed / import commands as Path A.

## What I need from you to finish “live”

Reply with **one** of:

1. “用 Render Blueprint” — and connect GitHub (or paste a repo URL after you push), **or**
2. Paste a Neon/Render **`DATABASE_URL`** + confirm Render/GitHub is linked so deploy can proceed.

Do not put production passwords in chat if avoidable; set them in the host dashboard.

## Local Docker (not public)

```bash
docker compose up --build
```
