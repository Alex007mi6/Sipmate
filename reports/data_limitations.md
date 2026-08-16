# SipMate Data Limitations

**Phase:** 2  
**Date:** 2026-08-11 (updated: default serving 375 ml)  
**Dataset:** `beer_profile_and_ratings.csv` (Beer Profile and Ratings corpus)

This note records limitations that affect recommendation behaviour, evaluation interpretation, and thesis claims. Do not overstate what the prototype can guarantee.

---

## 1. Serving size is a default stub (375 ml), not measured data

The source dataset does **not** include serving volume.

**Operational decision:** every cleaned/imported product is assigned:

```text
serving_ml = 375
alcohol_ml = serving_ml × abv / 100
alcohol_grams ≈ alcohol_ml × 0.789
```

Recommendation constraint uses:

```text
candidate.alcohol_ml < selected.alcohol_ml
```

falling back to ABV only if `alcohol_ml` were missing.

**Impact on research claim:** with a **uniform** default serving, `alcohol_ml` ranking is currently **mathematically equivalent** to ABV ranking. The per-serving formulation becomes empirically distinct only after admins set different `serving_ml` values (e.g. 330 ml bottle vs 568 ml pint).

**Mitigation:** product schema and admin UI allow per-product serving edits; changing serving/ABV recomputes alcohol fields and can mark the recommender model stale when needed.

Thesis text should state clearly that 375 ml is an **assumed default serving**, not observed pub pour data.

---

## 2. Beer-only product space

All 3197 products are beers (111 styles). The prototype does **not** currently cover wine, cider, spirits, RTDs, or mixed drinks common in broader “pub contexts.”

Thesis framing should describe SipMate as evaluated on a **beer substitution** corpus, with schema designed for later category expansion.

---

## 3. Suspicious ABV zeros

12 products have `ABV == 0` but styles/names consistent with ordinary alcoholic beers (often empty descriptions). They are flagged `abv_suspicious` and **excluded from recommendation** until verified.

They should **not** be treated as confirmed alcohol-free options for “Zero Hero” style gamification without manual validation.

With default serving, these rows also receive `alcohol_ml = 0`; they remain non-recommendable via the suspicious flag.

---

## 4. Missing taste profiles

12 products have all similarity taste features equal to 0. They are marked `missing_taste_profile` and excluded from recommendation. No imputation was applied (avoids fabricating sensory structure).

---

## 5. No product images

The dataset provides no image URLs or files. UI will use placeholders until administrators upload images via the storage service.

---

## 6. Sparse / placeholder descriptions

1347 rows have effectively empty descriptions after stripping `Notes:`. Search and UX must rely primarily on name, brand, style, and ABV—not long copy.

---

## 7. Taste feature provenance

Numeric taste scores derive from descriptor lexicons / review text analysis (see `Beer Descriptors Simplified.xlsx`), not lab chemistry or trained sensory panels. Similarity is **profile similarity in this feature space**, not guaranteed perceptual identity for every drinker.

---

## 8. Sensory `Alcohol` excluded

The integer `Alcohol` column is a mouthfeel/perception score correlated with ABV (~0.65). It is excluded from cosine similarity so “taste match” does not smuggle alcohol strength into the similarity metric. Ablation against including it is optional future work, not part of the default model.

---

## 9. IBU fields are style ranges

`Min IBU` / `Max IBU` are not used as product-level taste features.

---

## 10. Review scores unused

`review_*` and `number_of_reviews` are unused for recommendation to avoid popularity bias and stay within content-based, constraint + taste KNN design.

---

## 11. Extreme ABV specialty beers

A few products exceed 20% ABV (up to 57.5%). They are retained and flagged. With 375 ml serving they imply very high `alcohol_ml`; they can dominate reduction percentages when selected as the current drink. Evaluation metrics should report distributions, not only means.
