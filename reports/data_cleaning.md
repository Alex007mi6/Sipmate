# SipMate Data Cleaning Report

**Phase:** 2  
**Date:** 2026-08-11  
**Script:** `scripts/clean_data.py`  
**Input (immutable):** `data/raw/beer_profile_and_ratings.csv`  
**Output:** `data/processed/products_cleaned.csv`  
**Machine summary:** `data/processed/cleaning_summary.json`

---

## 1. Goals

- Produce a reproducible cleaned product table for PostgreSQL import and offline ML.
- Never modify raw data.
- Separate alcohol **constraint** fields from **taste similarity** fields.
- Flag rows that cannot safely participate in recommendation.

---

## 2. Pipeline steps

1. Load raw CSV from `data/raw/`.
2. Assert `Beer Name (Full)` uniqueness (natural key).
3. Standardise columns: `name`, `full_name`, `brand`, `category`, `description`, `abv`.
4. Clean descriptions: strip `Notes:` prefix, collapse whitespace, remove tabs.
5. Coerce ABV and taste columns to numeric.
6. Set default `serving_ml = 375` (source has no serving size; per-product editable later) and compute:
   `alcohol_ml = serving_ml × abv / 100`,
   `alcohol_grams ≈ alcohol_ml × 0.789`.
7. Flag:
   - `abv_suspicious` — ABV == 0 or NaN after coercion
   - `missing_taste_profile` — any NaN taste feature **or** all similarity features == 0
   - `abv_outlier` — ABV &gt; 20
   - `recommendable` — not suspicious ABV and not missing taste profile
8. Persist taste similarity columns (lowercase):  
   `astringency, body, bitter, sweet, sour, salty, fruits, hoppy, spices, malty`
9. **Exclude** sensory `Alcohol` from output taste vector (approved 2026-08-11).
10. Sort by `brand`, `full_name` for stable output; write CSV + JSON summary.

---

## 3. Duplicate handling

| Type | Count | Decision |
|------|------:|----------|
| Exact duplicate rows | 0 | N/A |
| Same short `Name`, different brewery | 131 | **Keep all** |
| Same `Brewery` + `Name` | 0 | N/A |
| Same `Beer Name (Full)` | 0 | Use as key |

No rows were deleted solely for name collisions.

---

## 4. Missing-value strategy

| Issue | Strategy | Rationale |
|-------|----------|-----------|
| Source NaNs | None observed | — |
| Individual taste zeros | Keep | Valid sensory intensity (esp. Salty) |
| All taste features 0 (12 rows) | `missing_taste_profile=true`, `recommendable=false` | Cannot build similarity vector |
| Empty descriptions | Keep empty string after cleaning | Do not invent copy |
| ABV == 0 (12 rows) | `abv_suspicious=true`, `recommendable=false` | Styles look like missing ABV, not confirmed AF |

No median/category imputation for taste: imputed taste would invent similarity structure and weaken thesis validity. Prefer exclude-from-recommender over synthetic fill.

---

## 5. ABV cleaning

- Source ABV already float; coerce with `pd.to_numeric`.
- Stored as numeric `abv`.
- Suspicious zeros flagged (not silently converted to alcohol-free).
- Outliers ABV &gt; 20 flagged (`abv_outlier`) but remain recommendable if taste profile is valid (real specialty beers).

---

## 6. Serving size / alcohol per serving

Source dataset contains **no serving size**.

**Decision (2026-08-11):** apply a uniform default stub:

- `serving_ml = 375` for every imported product  
- `alcohol_ml = serving_ml × abv / 100`  
- `alcohol_grams ≈ alcohol_ml × 0.789`

Primary recommendation constraint will use **`alcohol_ml`** (lower alcohol per serving).

Admins can change `serving_ml` (and/or ABV) per product later; alcohol fields must be recomputed on update. Documented caveat: equal default servings mean ranking by `alcohol_ml` is currently equivalent to ranking by ABV until servings diverge.

See `reports/data_limitations.md`.

---

## 7. Taste feature decisions

**Included in similarity vector:**  
Astringency, Body, Bitter, Sweet, Sour, Salty, Fruits, Hoppy, Spices, Malty

**Excluded:**

| Field | Reason |
|-------|--------|
| Alcohol (sensory) | Approved exclusion; correlates with ABV; belongs to constraint axis |
| ABV | Constraint only |
| Min/Max IBU | Style metadata |
| review_* / number_of_reviews | Quality/popularity, not taste profile for this study |

Scaling (`StandardScaler`) is deferred to Phase 3 training so scaler artifacts stay with the model.

---

## 8. Results (verified 2026-08-11)

| Metric | Value |
|--------|------:|
| Raw rows | 3197 |
| Cleaned rows written | 3197 (no hard deletes) |
| Recommendable | 3173 |
| `abv_suspicious` | 12 |
| `missing_taste_profile` | 12 |
| Excluded from recommendation (union) | 24 |
| `abv_outlier` (&gt;20) | 3 |

Non-recommendable products remain in the cleaned catalog for transparency and possible admin correction after PostgreSQL import (`is_active` / feature fixes).

---

## 9. How to reproduce

```bash
# from repository root
py -3 scripts/clean_data.py
```

Outputs:

- `data/processed/products_cleaned.csv`
- `data/processed/cleaning_summary.json`
