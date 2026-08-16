# SipMate Data Exploration Report

**Phase:** 1  
**Date:** 2026-08-11  
**Source:** `data/raw/beer_profile_and_ratings.csv` (mirrored from `Beer Dataset/`; raw files not modified)

---

## 1. Dataset inventory

| File | Rows | Columns | Role |
|------|------|---------|------|
| `beer_profile_and_ratings.csv` | 3197 | 25 | **Primary** product + taste dataset |
| `Beer Name Fuzzy Match List.csv` | 1088 | 2 | Optional name normalisation aid |
| `Brewery Name Fuzzy Match List.csv` | 87 | 2 | Optional brewery normalisation aid |
| `Beer Descriptors Simplified.xlsx` | lexicon sheets | — | Explains descriptor → score derivation; not product rows |

**Selected primary dataset:** `beer_profile_and_ratings.csv`  
Reason: only file with per-product ABV and numeric taste attributes suitable for constraint-based KNN recommendation.

---

## 2. Shape and schema

- **Rows:** 3197  
- **Columns:** 25  
- **Exact duplicate rows:** 0  
- **Unique `Beer Name (Full)`:** 3197 (usable natural key)  
- **Unique `Name`:** 3066 (131 short-name collisions across breweries)  
- **Unique `Brewery` + `Name`:** 3197  
- **Styles:** 111  
- **Breweries:** 934  

### Field list and dtypes

| Field | dtype | nulls | notes |
|-------|-------|------:|-------|
| Name | string | 0 | short product name |
| Style | string | 0 | category |
| Brewery | string | 0 | brand |
| Beer Name (Full) | string |.0 | brewery + name; unique |
| Description | string | 0 | often placeholder `Notes:` |
| ABV | float64 | 0 | alcohol by volume % |
| Min IBU | int64 | 0 | style range, not product sensory |
| Max IBU | int64 | 0 | style range |
| Astringency | int64 | 0 | taste feature |
| Body | int64 | 0 | taste feature |
| Alcohol | int64 | 0 | **sensory mouthfeel, not ABV** |
| Bitter | int64 | 0 | taste feature |
| Sweet | int64 | 0 | taste feature |
| Sour | int64 | 0 | taste feature |
| Salty | int64 | 0 | taste feature (many true zeros) |
| Fruits | int64 | 0 | taste feature |
| Hoppy | int64 | 0 | taste feature |
| Spices | int64 | 0 | taste feature |
| Malty | int64 | 0 | taste feature |
| review_aroma | float64 | 0 | rating — not for similarity |
| review_appearance | float64 | 0 | rating |
| review_palate | float64 | 0 | rating |
| review_taste | float64 | 0 | rating |
| review_overall | float64 | 0 | rating |
| number_of_reviews | int64 | 0 | popularity |

---

## 3. Missing values

Source CSV reports **zero NaNs** across all columns.

However, structural “missingness” exists:

| Pattern | Count | Interpretation |
|---------|------:|----------------|
| Description length ≤ 6 (`Notes:`) | 1347 | empty marketing copy |
| All selected taste features == 0 | 12 | unusable taste profile |
| ABV == 0 | 12 | likely missing ABV (ordinary styles), not labelled alcohol-free |

`Salty == 0` for 1895 rows is **not** treated as missing — most beers are not salty.

---

## 4. Duplicates

| Check | Count | Action |
|-------|------:|--------|
| Exact row duplicates | 0 | none |
| Duplicate short `Name` | 131 | keep; different breweries (e.g. many “Oktoberfest”) |
| Duplicate `Brewery` + `Name` | 0 | none |
| Duplicate `Beer Name (Full)` | 0 | use as natural key |

Do **not** drop short-name duplicates.

---

## 5. Alcohol variables

### ABV

| Stat | Value |
|------|------:|
| min | 0.0 |
| p1 | 0.5 |
| p5 | 4.0 |
| median | 6.0 |
| p95 | 11.0 |
| p99 | 13.4 |
| max | 57.5 |
| ABV &lt; 0.5 | 19 |
| ABV &lt; 3 | 73 |
| ABV &gt; 15 | 14 |
| ABV &gt; 20 | 3 |

Extreme high-ABV specialty beers (e.g. Schorschbock 57%) appear real; flag as outliers, do not auto-delete.

### Serving size

**Not present** in the source dataset. **Cleaning decision (2026-08-11):** default `serving_ml = 375` for all products, then derive `alcohol_ml` and `alcohol_grams`. Values are editable per product after import. Until servings differ, alcohol-per-serving constraint is equivalent to ABV constraint.

### Sensory `Alcohol` vs `ABV`

Pearson correlation ≈ **0.65**. Sensory `Alcohol` measures perceived alcoholic character, not % ABV.

**Decision (approved):** exclude sensory `Alcohol` from cosine taste similarity. Alcohol **constraint** uses derived `alcohol_ml` from default 375 ml serving (per-product adjustable later).

---

## 6. Taste attributes

Candidate similarity features (numeric):

`Astringency`, `Body`, `Bitter`, `Sweet`, `Sour`, `Salty`, `Fruits`, `Hoppy`, `Spices`, `Malty`

| Feature | min | max | zero count |
|---------|----:|----:|-----------:|
| Astringency | 0 | 81 | 33 |
| Body | 0 | 175 | 20 |
| Bitter | 0 | 150 | 31 |
| Sweet | 0 | 263 | 20 |
| Sour | 0 | 284 | 36 |
| Salty | 0 | 48 | 1895 |
| Fruits | 0 | 175 | 43 |
| Hoppy | 0 | 172 | 31 |
| Spices | 0 | 184 | 146 |
| Malty | 0 | 239 | 17 |

12 rows have **all** of the above equal to 0 (disjoint from the 12 ABV==0 rows).

---

## 7. Images

No image URL or binary fields in any dataset file. Product images must be placeholders and/or admin uploads.

---

## 8. Field classification for SipMate

### Product metadata

`Name`, `Beer Name (Full)`, `Brewery`, `Style`, `Description`

### Alcohol constraint variables

`alcohol_ml` (primary; from `serving_ml` default 375 × `abv / 100`), `abv` (fallback / display), `serving_ml`, `alcohol_grams`

### Taste features (similarity)

`Astringency`, `Body`, `Bitter`, `Sweet`, `Sour`, `Salty`, `Fruits`, `Hoppy`, `Spices`, `Malty`

### Must not use for taste similarity

- `ABV` (constraint only)  
- `Alcohol` (sensory; excluded by design decision)  
- `Min IBU`, `Max IBU`  
- all `review_*`, `number_of_reviews`

---

## 9. Implications for later phases

1. Cleaning must preserve all distinct `full_name` products; only flag non-recommendable rows.  
2. Offline recommender should train/evaluate on **recommendable** subset only.  
3. Limitations report must state default-375 ml serving assumption and beer-only corpus.  
4. Import into PostgreSQL should map cleaned columns + JSON taste features.
