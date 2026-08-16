# SipMate Offline Evaluation

**Phase:** 4  
**Generated (UTC):** 2026-08-11T11:23:33.870895+00:00  
**Model products:** 3173  
**Top-K:** 3

## Method

For every product in the fitted recommender index:

1. Request Top-3 constrained recommendations.
2. Constraint: `candidate.alcohol_ml < selected.alcohol_ml` (ABV fallback if needed).
3. Ranking: cosine distance on StandardScaler-normalised taste features.
4. Aggregate thesis metrics below.

Taste features exclude sensory `Alcohol` and ABV (constraint axis only).

## Metrics

| Metric | Value |
|--------|------:|
| Constraint Satisfaction Rate | 100.00% |
| Recommendation pairs checked | 9512 |
| Average Cosine Similarity | 0.9204 |
| Average Taste Match % | 92.04 |
| Average ABV Reduction (pp) | 1.399 |
| Average ABV Reduction % | 20.36 |
| Average alcohol_ml Reduction | 5.245 |
| Average alcohol_ml Reduction % | 20.36 |
| Recommendation Coverage | 99.97% |
| No-Recommendation Rate | 0.03% |
| Products with ≥1 recommendation | 3172 |
| Products with 0 recommendations | 1 |
| Self-recommendations (should be 0) | 0 |

## No-recommendation reasons

| Reason | Count |
|--------|------:|
| `NO_CANDIDATES` | 1 |

## Interpretation notes

- With uniform default `serving_ml = 375`, alcohol_ml reductions track ABV reductions.
- Constraint satisfaction should be ~100% by construction of the filter.
- Lowest-alcohol products naturally drive the no-recommendation rate.
- Machine-readable copy: `reports/offline_evaluation.json`.
