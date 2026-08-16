# SipMate System Design

**Version:** 0.1 (Phase 0)  
**Date:** 2026-08-11  
**Status:** Approved for implementation (2026-08-11) — sensory `Alcohol` excluded from taste vector  
**Thesis focus:** Design and Offline Evaluation of SipMate: A Gamified Machine-Learning-Based Recommendation System for Responsible Drinking in Pub Contexts

---

## 0. Repository audit summary

### Current state

| Item | Finding |
|------|---------|
| Project root | `C:\Users\Hasee\Desktop\Sipmate` |
| Source code | **None** (greenfield) |
| Git | **Not initialised** |
| README / requirements / package.json | **Absent** |
| Existing folders | Only `Beer Dataset/` |
| Local tooling | Python 3.14 (`py -3`), Node v24.19, npm 11.17, Git 2.51 |
| Missing tooling | Docker CLI, `gh`, local `psql`, hosting credentials |

### Datasets found

| File | Role | Rows × Cols | Use in SipMate |
|------|------|-------------|----------------|
| `Beer Dataset/beer_profile_and_ratings.csv` | **Primary product + taste dataset** | 3197 × 25 | Source of truth for initial import |
| `Beer Dataset/Beer Name Fuzzy Match List.csv` | Name normalisation helpers | 1088 × 2 | Optional cleaning aid only |
| `Beer Dataset/Brewery Name Fuzzy Match List.csv` | Brewery normalisation helpers | 87 × 2 | Optional cleaning aid only |
| `Beer Dataset/Beer Descriptors Simplified.xlsx` | Descriptor lexicon (Mouthfeel / Taste / Flavor) | reference sheets | Explains how taste scores were derived; **not** product rows |

### Primary dataset field classification

**Product metadata**

- `Name`, `Beer Name (Full)`, `Brewery`, `Style`, `Description`

**Alcohol constraint**

- `ABV` (numeric, 0.0–57.5). Source CSV has **no serving size**; cleaning applies a **default `serving_ml = 375`** and computes `alcohol_ml` / `alcohol_grams`. Primary recommendation constraint uses **alcohol per serving** (`alcohol_ml`). Admins can change `serving_ml` per product later (recomputes alcohol fields; may mark model stale).

**Taste features (similarity variables)**

- `Astringency`, `Body`, `Bitter`, `Sweet`, `Sour`, `Salty`, `Fruits`, `Hoppy`, `Spices`, `Malty`
- `Alcohol` (integer mouthfeel/perception score, **not** ABV). Correlated with ABV (r≈0.65). **Decision (approved 2026-08-11): exclude from similarity vector** so alcohol strength stays on the constraint axis only. Documented in exploration/cleaning reports.

**Do not use for recommendation similarity**

- `Min IBU`, `Max IBU` (style range metadata, not product-specific sensory scores)
- `review_aroma`, `review_appearance`, `review_palate`, `review_taste`, `review_overall`, `number_of_reviews` (popularity / quality ratings — collaborative-signal adjacent; out of scope)

**Missing for product UX**

- No image URLs/files in dataset → placeholders + admin upload required
- No native serving size in CSV → default **375 ml** stub + derived alcohol-per-serving; per-product editable later (see `reports/data_limitations.md`)

---

## 1. System architecture

### Recommended approach (Approach A — modular monolith)

```text
Mobile browser
    │ HTTPS
    ▼
Vite React SPA  ──REST/JSON──►  FastAPI (Python)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              PostgreSQL      StorageService    Recommender
              (source of      (local uploads/   (joblib KNN
               truth for       or S3/Cloudinary) + StandardScaler)
               products,
               users,
               gamification)
```

**Why this approach**

- Matches the required thesis stack exactly
- Single backend process: easier to deploy, test, and explain in a dissertation
- Clear service boundaries inside one codebase (API → services → domain modules)
- PostgreSQL remains product source of truth after first CSV import

### Alternatives considered

| Approach | Description | Trade-off |
|----------|-------------|-----------|
| **A (chosen)** | FastAPI + React Vite SPA + PostgreSQL + storage abstraction | Best fit for requirements and paper narrative |
| **B** | Next.js full-stack + Python ML microservice | Extra hop, dual language runtime complexity; violates “keep it simple” |
| **C** | Microservices (auth, recs, gamification) | Explicitly out of scope; over-engineered for prototype |

### Runtime environments

| Environment | DB | Images | Auth cookies |
|-------------|----|--------|--------------|
| Local (Docker Compose when available) | PostgreSQL container | `uploads/` | Secure=false, SameSite=Lax |
| Local (Windows without Docker) | Managed Postgres (Neon/Supabase) or local Postgres install | `uploads/` | same |
| Production | Managed PostgreSQL | Cloudinary or S3-compatible | Secure=true, SameSite=Lax/None as needed |

---

## 2. Frontend architecture

**Stack:** React + TypeScript + Vite + CSS (or Tailwind if scaffolding is faster without fighting the design rules)

**Layout principles**

- Mobile-first PWA-like web app (not native)
- Pub-friendly: large tap targets, short copy, recommendation page as primary surface
- Guest-first: no forced login on home
- Route-level code splitting for admin

**Key routes**

| Route | Purpose |
|-------|---------|
| `/` | Home + CTA “Find a Lighter Choice” |
| `/drinks` | Search / filter / select current drink |
| `/recommend` | Current vs lighter alternatives + accept |
| `/ladder` | Lighter Ladder visualisation |
| `/login`, `/register` | Auth |
| `/profile` | Points, badges, history |
| `/rewards`, `/redemptions` | Catalog + codes |
| `/admin/*` | Products, model, rewards, redemptions |
| `/privacy` | Short privacy notice |

**State**

- Server state via fetch wrappers (React Query optional; keep thin if unused)
- Auth via HttpOnly cookie; frontend only knows “logged in / role”
- Anonymous `session_id` in `sessionStorage` for recommendation_events

**UI components (thin)**

- `DrinkCard`, `RecommendationCompare`, `LighterLadder`, `PointsBadge`, `RedeemModal`
- No heavy design system; shared CSS variables for brand colours

---

## 3. Backend architecture

```text
backend/app/
  api/            # FastAPI routers (thin)
  schemas/        # Pydantic request/response
  models/         # SQLAlchemy ORM
  services/       # Product, Auth, Gamification, Rewards, ModelAdmin
  recommender/    # Feature prep + KNN engine
  auth/           # password hashing, cookie session/JWT
  gamification/   # points rules, badges, anti-abuse
  storage/        # LocalStorage / Cloudinary / S3 adapters
  core/           # config, logging, errors, deps
```

**Layering rule**

```text
Router → Service → ORM / Recommender / Storage
```

No business logic in routers. Recommender never talks HTTP.

**Config:** Pydantic Settings from environment; `.env.example` committed; secrets never committed.

---

## 4. Database structure

PostgreSQL via SQLAlchemy 2.x + Alembic.

### Entity-relationship (logical)

```text
users 1──* points_transactions
users 1──* user_badges *──1 badges
users 1──* redemptions *──1 rewards
users 1──* recommendation_events (nullable user)

products 1──* recommendation_events (selected / recommended)

model_versions (singleton active + history)

gamification_rules (config table or seeded rows)
```

### Tables (minimum)

**users**  
`id`, `email` (unique), `password_hash`, `display_name`, `role` (`user`|`admin`), `research_consent` (bool, default false), `is_active`, `created_at`, `updated_at`

**products**  
`id`, `name`, `full_name` (unique natural key from `Beer Name (Full)`), `brand` (brewery), `category` (style), `description`, `abv`, `serving_ml` (default 375 on import; admin-editable), `alcohol_ml`, `alcohol_grams`, `taste_features` (JSONB, fixed keys), `image_url`, `image_key`, `is_active`, `created_at`, `updated_at`

**model_versions**  
`id`, `algorithm`, `feature_names` (JSONB), `dataset_version`, `model_path`, `scaler_path`, `metadata_path`, `status` (`active`|`stale`|`archived`|`failed`), `product_count`, `created_at`, `activated_at`

**points_transactions**  
`id`, `user_id`, `event_type`, `points` (signed int), `reference_id`, `metadata` (JSONB), `created_at`  
Unique constraint on `(user_id, event_type, reference_id)` where `reference_id` is not null — primary anti-farming control

**badges** / **user_badges**  
Configurable definitions + earn ledger (`user_id`, `badge_id` unique)

**rewards**  
`id`, `name`, `description`, `image_url`, `image_key`, `points_cost`, `stock`, `active`, timestamps

**redemptions**  
`id`, `user_id`, `reward_id`, `points_spent`, `redemption_code` (unique), `status` (`pending`|`redeemed`|`cancelled`), `created_at`, `redeemed_at`

**recommendation_events**  
`id`, `user_id` nullable, `anonymous_session_id` nullable, `selected_product_id`, `recommended_product_id` nullable, `similarity_score`, `alcohol_reduction`, `event_type`, `created_at`

**gamification_rules**  
`event_type`, `points`, `cooldown_seconds`, `enabled`, `metadata`

Indexes on product search (`name`, `brand`, `category`), redemption code, user email.

Soft-delete products via `is_active=false` to preserve historical events.

---

## 5. Recommendation model structure

### Algorithm

- Constraint-based filtering, then **k-nearest neighbours** with **cosine distance**
- Implementation: `sklearn.neighbors.NearestNeighbors(metric="cosine")`
- Paper wording: *KNN finds nearest neighbours; cosine distance is the similarity metric* (not two separate models)

### Constraint

1. If both products have non-null `alcohol_ml` (or computable from `serving_ml` + `abv`):  
   `candidate.alcohol_ml < selected.alcohol_ml`
2. Else:  
   `candidate.abv < selected.abv`
3. Candidate must be `is_active` and have complete taste vector
4. Never recommend the selected product itself

### Similarity features (planned default)

```text
Astringency, Body, Bitter, Sweet, Sour, Salty, Fruits, Hoppy, Spices, Malty
```

Exclude: `ABV`, `Alcohol` (perception), reviews, IBU ranges.

### Preprocessing

1. Numeric cast  
2. Drop or mark rows missing required taste features (strategy locked in Phase 2 report)  
3. `StandardScaler` fit on training matrix  
4. Persist `models/scaler.joblib`, `models/recommender.joblib`, `models/model_metadata.json`

### Online serve

1. Load active model version paths from DB / metadata  
2. Build selected vector with same feature order + scaler  
3. Filter candidates by constraint in DB (or in-memory index of active products)  
4. Query neighbours among filtered set (fit subset or distance to all then filter — for ~3k products, in-memory filter-then-rank is acceptable)  
5. Return Top 3 with user-facing scores:

- `taste_match_pct = round((1 - cosine_distance) * 100)` clamped sensibly  
- `abv_reduction` / `alcohol_reduction_pct`

### No-recommendation cases

Return HTTP 200 with empty `recommendations` + `reason` code (`ALREADY_LIGHTEST`, `NO_CANDIDATES`, `MISSING_FEATURES`, `MODEL_UNAVAILABLE`). Frontend shows friendly copy. Never 500 for empty result sets.

### Model staleness

Product changes to ABV / serving / alcohol / taste / `is_active` → mark active `model_versions.status = stale`.  
Image/description-only edits → no rebuild required.  
Admin **Rebuild Recommendation Model**: reload active products → preprocess → fit → write artifacts → new active version.

---

## 6. Image storage scheme

```text
StorageService (interface)
  ├── LocalStorageService      # uploads/  (dev)
  ├── CloudinaryStorageService # production option A
  └── S3CompatibleStorageService # production option B
```

- DB stores `image_url` + `image_key` only  
- Upload validates MIME (`image/jpeg|png|webp`), size limit (e.g. 2–5 MB), and basic image decode  
- Replace: upload new → update DB → delete old key best-effort  
- Dataset has no images: seed with deterministic placeholder path or generated SVG initials until admin uploads

---

## 7. User identity & authentication

- **Guest mode default** — full recommend + ladder without account  
- Register / Login / Logout / Me  
- Passwords: bcrypt or Argon2 via `passlib` / `pwdlib`  
- Session: **JWT in HttpOnly cookie** (or signed session cookie); **not** localStorage  
- Cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure` in production  
- Roles: `user`, `admin`; admin routes dependency-checked  
- Demo admin created from env vars at seed time (password not committed)

---

## 8. Points system

- Append-only **points_transactions** ledger  
- Balance = `SUM(points)` for user (optional cached column later; not required)  
- Rules from `gamification_rules` / config — **not** hardcoded in frontend  
- Example events (exact values configurable):

| Event | Typical points | Notes |
|-------|----------------|-------|
| `LIGHTER_CHOICE_ACCEPTED` | +10 | First time per selected→accepted pair |
| `ALCOHOL_FREE_CHOICE` | +20 | Accepted candidate ABV ≈ 0 |
| `LADDER_MILESTONE` | +15 | Milestone reference unique |
| Reward redeem | negative | Ledger entry + redemption row |

**Anti-abuse (prototype-level)**

- Unique `(user_id, event_type, reference_id)`  
- Optional cooldown per event type  
- Guests can accept lighter choice but do **not** earn points until login (prompt, not hard block)

**Forbidden rewards**

- No points for volume consumed, alcohol purchases, or “more drinks”

---

## 9. Badge system

- `badges` table: `condition_type`, `threshold`, icon path, active flag  
- Seed examples: First Lighter Step, Lighter Explorer (3), Ladder Climber, Zero Hero  
- Awarded in `GamificationService` after successful ledger events  
- Frontend only displays; conditions evaluated server-side

---

## 10. Rewards & redemption

**Prototype workflow (no POS)**

1. User redeem → check login, points, stock, active  
2. DB transaction: lock reward row / user balance check → insert negative ledger → decrement stock → create `redemptions` with unique code → commit  
3. Show code + `pending`  
4. Admin confirms code → `pending` → `redeemed` atomically; code single-use  

Concurrent redeem tests required so balance cannot go negative.

---

## 11. Admin backend

Protected `/api/admin/*` + `/admin` UI:

- Products CRUD (soft deactivate), taste/ABV/serving edits, image upload/replace  
- Rewards CRUD + stock/cost/active  
- Redemption search + confirm  
- Model status + Rebuild  
- Mark model stale on relevant product writes

---

## 12. Data flow

### Bootstrap (once / reproducible)

```text
Beer Dataset (raw, immutable)
  → scripts/clean_data.py
  → data/processed/products_cleaned.csv
  → scripts/import_products.py → PostgreSQL products
  → scripts/train_recommender.py (or admin rebuild)
  → models/*.joblib + model_versions row
  → scripts/seed.py (badges, rules, rewards, admin)
```

### Runtime product truth

```text
Admin / import → PostgreSQL products → (if features changed) model STALE
Admin rebuild → fit from DB → new model_versions ACTIVE
```

### User recommendation path

```text
Select drink → POST /api/recommendations
  → load product + model
  → constrain lower alcohol
  → KNN cosine among candidates
  → return Top 3 + ladder steps
  → log RECOMMENDATION_SHOWN
Accept → optional gamification if authenticated
```

---

## 13. API design (REST)

Uniform error body:

```json
{ "error": { "code": "INSUFFICIENT_POINTS", "message": "Not enough points.", "details": {} } }
```

### Public / shared

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | liveness |
| GET | `/api/products` | search, style filter, pagination |
| GET | `/api/products/{id}` | detail |
| POST | `/api/recommendations` | `{ product_id, top_k?, session_id? }` |
| POST | `/api/recommendations/ladder` | lighter ladder for product |
| POST | `/api/auth/register` | |
| POST | `/api/auth/login` | sets cookie |
| POST | `/api/auth/logout` | clears cookie |
| GET | `/api/auth/me` | |
| GET | `/api/profile` | points, badges summary |
| GET | `/api/rewards` | active catalog |
| POST | `/api/rewards/{id}/redeem` | auth required |
| GET | `/api/redemptions` | current user |
| POST | `/api/gamification/events` | accept lighter choice etc. |

### Admin

| Method | Path |
|--------|------|
| CRUD | `/api/admin/products` |
| POST | `/api/admin/products/{id}/image` |
| GET/POST | `/api/admin/model/status`, `/api/admin/model/rebuild` |
| CRUD | `/api/admin/rewards` |
| GET | `/api/admin/redemptions` |
| POST | `/api/admin/redemptions/{code}/confirm` |

Status codes: 400 validation, 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict (duplicate redeem / email), 422 semantic, 500 unexpected (no traceback to client).

---

## 14. Deployment approach

**Goal:** simplest HTTPS-capable stack for a thesis prototype.

**Proposed production topology**

1. **PostgreSQL:** Neon or Supabase (free/low-cost managed)  
2. **Backend + static frontend:** Railway **or** Render Web Service  
   - Build frontend → FastAPI serves `frontend/dist` in production **or** separate static host  
   - Prefer **single service serving API + built SPA** to minimise moving parts  
3. **Images:** Cloudinary free tier (simple) or R2/S3  
4. **CI:** GitHub Actions — pytest, frontend test/build on push/PR  

**Local:** `docker-compose.yml` with `db`, `api`, `web` (and volume for uploads). Note: Docker is **not** currently installed on this machine; Compose files still shipped; Windows dev can use managed DB without Docker.

**Deployment readiness rule:** do not claim deployed until `/health` and core flows verified on a public URL. If hosting login is missing, prepare all config/docs and list exact secrets the user must provide.

---

## 15. Security measures

- Password hashing (bcrypt/Argon2)  
- HttpOnly cookie auth; Secure in production  
- Admin authorisation on every admin route  
- CORS allowlist via env  
- Pydantic validation; SQLAlchemy bound parameters  
- Upload MIME/size/image checks  
- Rate limit auth + redeem endpoints (slowapi or equivalent)  
- Secrets only via environment; `.env` gitignored  
- No passwords/tokens in logs  
- Data minimisation; short Privacy Notice; optional `research_consent`  
- Atomic redemptions; unique codes; no negative balances  

---

## 16. Testing strategy

| Layer | Tool | Focus |
|-------|------|-------|
| Data cleaning | pytest | ABV parse, duplicates, alcohol calc when serving present |
| Recommender | pytest | constraint, no self-match, ranking, empty candidates |
| Auth | pytest + httpx AsyncClient | register/login/wrong password/admin gate |
| Points | pytest | award, duplicate block, ledger sum |
| Redemption | pytest | insufficient points, stock, concurrent safety |
| Products/admin | pytest | CRUD, soft delete, image replace |
| Frontend | Vitest + Testing Library | critical components / happy paths |
| CI | GitHub Actions | backend tests + frontend test/build |

Manual Phase 16 checklist remains the Definition of Done gate.

---

## Target repository layout

```text
sipmate/
  frontend/                 # React + TS + Vite
  backend/
    app/
      api/
      models/
      schemas/
      services/
      recommender/
      auth/
      gamification/
      storage/
      core/
    tests/
  data/
    raw/                    # copy or documented pointer to Beer Dataset (immutable)
    processed/
  models/
  scripts/
    clean_data.py
    import_products.py
    train_recommender.py
    evaluate_recommender.py
    seed.py
  reports/
  docs/
    sipmate-system-design.md
  alembic/
  docker/
  .github/workflows/ci.yml
  docker-compose.yml
  README.md
  .env.example
```

Preserve `Beer Dataset/` as raw input (or copy into `data/raw/` without mutation).

---

## Implementation phases (binding order)

| Phase | Deliverable |
|-------|-------------|
| 0 | Audit + this design (current) |
| 1 | `reports/data_exploration.md` |
| 2 | Cleaning pipeline + `data/processed` + cleaning/limitations reports |
| 3 | Offline recommender engine |
| 4 | Offline evaluation reports/JSON |
| 5 | PostgreSQL models + Alembic |
| 6 | Import script |
| 7 | Product + recommendation APIs |
| 8 | Frontend core loop (select → recommend → ladder) |
| 9 | Auth (guest + registered) |
| 10 | Points + badges |
| 11 | Rewards + redemption codes |
| 12 | Admin dashboard |
| 13 | Automated tests hardening |
| 14 | Docker + production config |
| 15 | Deploy (when credentials available) |
| 16 | Full verification checklist |

**Hard gate:** Phase 8 core loop must work on real data before expanding gamification UI polish.

---

## Known risks & decisions

| Risk | Impact | Mitigation |
|------|--------|------------|
| No native `serving_ml` in CSV | Need per-serving alcohol constraint for thesis goal | Default **375 ml** on clean/import; compute `alcohol_ml` / `alcohol_grams`; admin can edit per product |
| `Alcohol` column vs `ABV` confusion | Incorrect features / paper weakness | Exclude from taste vector by default; explain in reports |
| ABV = 0 rows (12) may be missing data, not true AF | Misleading Zero Hero / AF ladder | Flag in cleaning; treat 0 as suspicious unless description confirms; optional exclude from AF badges until verified |
| Extreme ABV (e.g. 57.5%) | Distorts reductions | Cap/filter outliers in cleaning with documented rule |
| No product images | Weak mobile UX | Placeholders + admin upload |
| Beer-only corpus | Thesis mentions “pub” drinks broadly | Scope statement: prototype evaluates beer substitutes; architecture allows later categories |
| Python 3.14 very new | Package wheels may lag | Pin compatible versions; CI may use 3.12 if needed |
| No Docker / gh / hosting creds on machine | Local compose & deploy blocked | Ship Compose + deploy docs; use managed Postgres for early Phases; ask user for platform login when Phase 15 starts |
| Name duplicates (131) but unique Full Name | Wrong merge risk | Use `Beer Name (Full)` as natural key |
| Description often short (`Notes:` only) | Limited UX copy | Keep field; don’t invent text |

---

## Design decisions (locked)

| Decision | Choice | Date |
|----------|--------|------|
| Sensory `Alcohol` in cosine taste vector | **Excluded** | 2026-08-11 |
| Alcohol constraint | Primary: **`alcohol_ml`** from default 375 ml serving (per-product editable) | 2026-08-11 |
| Architecture | Approach A modular monolith | 2026-08-11 |

---

## Approval gate

Design approved. Phase 1+ may proceed.  
Next: Phase 1 — Dataset Exploration → `reports/data_exploration.md`, then Phase 2 cleaning.