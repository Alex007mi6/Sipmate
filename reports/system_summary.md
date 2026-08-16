# SipMate System Summary

**Date:** 2026-08-11  
**Purpose:** Concise overview for thesis writing.

## Architecture

Modular monolith: React + TypeScript (Vite) frontend, FastAPI backend, PostgreSQL source of truth, joblib artifacts for the recommender, local/object storage for images.

## Dataset

Beer Profile and Ratings corpus (`beer_profile_and_ratings.csv`, 3197 beers). Cleaned to 3173 recommendable products after flagging suspicious ABV=0 and missing taste profiles.

## Preprocessing

- Default serving size **375 ml** (assumed; per-product editable).
- `alcohol_ml = serving_ml × ABV / 100`; `alcohol_grams ≈ alcohol_ml × 0.789`.
- Taste features: astringency, body, bitter, sweet, sour, salty, fruits, hoppy, spices, malty.
- Sensory `Alcohol` excluded from similarity (approved).
- `StandardScaler` fit on recommendable products.

## Recommendation algorithm

Constraint-based **Nearest Neighbours** with **cosine distance**:

1. Filter candidates with strictly lower `alcohol_ml` (ABV fallback if needed).
2. Rank by cosine distance on scaled taste vectors.
3. Return Top-3 with user-facing taste match % and alcohol reduction %.

Offline evaluation (Top-3 over model index): constraint satisfaction **100%**, coverage **≈99.97%**, mean cosine similarity **≈0.92**.

## Database

PostgreSQL via SQLAlchemy + Alembic. Entities include users, products, model_versions, points_transactions, badges, rewards, redemptions, recommendation_events, gamification_rules.

## Gamification

Points ledger (append-only), configurable rules, badges for lighter / alcohol-free / ladder milestones, anti-duplicate via `(user_id, event_type, reference_id)`. Guests can accept recommendations without forced login; points require authentication.

## Rewards

Prototype voucher workflow with unique codes and admin confirmation. Atomic redeem prevents negative balances.

## Deployment

Docker Compose for local Postgres + API. Production intended as single FastAPI service + managed Postgres + HTTPS cookies. Hosting credentials were not available in the development environment at authoring time.
