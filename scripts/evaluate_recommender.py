"""
Offline evaluation of SipMate recommender for thesis metrics.

Usage (repo root):
    py -3 scripts/evaluate_recommender.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.recommender import SipMateRecommender  # noqa: E402
from app.recommender.features import DEFAULT_TOP_K  # noqa: E402

MODELS_DIR = ROOT / "models"
REPORT_MD = ROOT / "reports" / "offline_evaluation.md"
REPORT_JSON = ROOT / "reports" / "offline_evaluation.json"


def evaluate(model: SipMateRecommender, top_k: int = DEFAULT_TOP_K) -> dict:
    assert model.meta_df is not None

    n = model.n_products
    keys = model.product_keys

    constraint_checks: list[bool] = []
    similarities: list[float] = []
    abv_reductions: list[float] = []
    abv_reduction_pcts: list[float] = []
    alc_reductions: list[float] = []
    alc_reduction_pcts: list[float] = []
    self_recs = 0
    with_recs = 0
    without_recs = 0
    reason_counts: dict[str, int] = {}

    for key in keys:
        result = model.recommend(key, top_k=top_k)
        if not result.recommendations:
            without_recs += 1
            reason = result.reason or "UNKNOWN"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            continue

        with_recs += 1
        selected = model.meta_df.iloc[model.key_to_index[key]]
        selected_abv = float(selected["abv"])
        selected_alc = float(selected["alcohol_ml"]) if pd.notna(selected["alcohol_ml"]) else None

        for rec in result.recommendations:
            if rec.product_key == key:
                self_recs += 1
            ok = True
            if selected_alc is not None and rec.alcohol_ml is not None:
                ok = rec.alcohol_ml < selected_alc
            else:
                ok = rec.abv < selected_abv
            constraint_checks.append(ok)
            similarities.append(1.0 - rec.cosine_distance)
            abv_reductions.append(rec.abv_reduction)
            abv_reduction_pcts.append(rec.abv_reduction_pct)
            if rec.alcohol_ml_reduction is not None:
                alc_reductions.append(rec.alcohol_ml_reduction)
            if rec.alcohol_ml_reduction_pct is not None:
                alc_reduction_pcts.append(rec.alcohol_ml_reduction_pct)

    def _mean(xs: list[float]) -> float | None:
        return float(np.mean(xs)) if xs else None

    metrics = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_products_in_model": n,
        "top_k": top_k,
        "constraint_satisfaction_rate": (
            float(np.mean(constraint_checks)) if constraint_checks else None
        ),
        "n_recommendation_pairs_checked": len(constraint_checks),
        "average_cosine_similarity": _mean(similarities),
        "average_taste_match_pct": (
            None if not similarities else float(np.mean([(s * 100.0) for s in similarities]))
        ),
        "average_abv_reduction": _mean(abv_reductions),
        "average_abv_reduction_pct": _mean(abv_reduction_pcts),
        "average_alcohol_ml_reduction": _mean(alc_reductions),
        "average_alcohol_ml_reduction_pct": _mean(alc_reduction_pcts),
        "recommendation_coverage": with_recs / n if n else 0.0,
        "no_recommendation_rate": without_recs / n if n else 0.0,
        "n_with_at_least_one_recommendation": with_recs,
        "n_with_no_recommendation": without_recs,
        "self_recommendation_count": self_recs,
        "no_recommendation_reasons": reason_counts,
        "model_metadata": {
            "dataset_version": model.metadata.get("dataset_version"),
            "feature_names": model.metadata.get("feature_names"),
            "metric": model.metadata.get("metric"),
            "constraint_primary": model.metadata.get("constraint_primary"),
            "created_at_utc": model.metadata.get("created_at_utc"),
        },
    }
    return metrics


def write_markdown(metrics: dict) -> None:
    def pct(x: float | None) -> str:
        if x is None:
            return "n/a"
        return f"{x * 100:.2f}%"

    def num(x: float | None, digits: int = 4) -> str:
        if x is None:
            return "n/a"
        return f"{x:.{digits}f}"

    reasons = metrics.get("no_recommendation_reasons") or {}
    reason_lines = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(reasons.items())) or "| — | 0 |"

    md = f"""# SipMate Offline Evaluation

**Phase:** 4  
**Generated (UTC):** {metrics["generated_at_utc"]}  
**Model products:** {metrics["n_products_in_model"]}  
**Top-K:** {metrics["top_k"]}

## Method

For every product in the fitted recommender index:

1. Request Top-{metrics["top_k"]} constrained recommendations.
2. Constraint: `candidate.alcohol_ml < selected.alcohol_ml` (ABV fallback if needed).
3. Ranking: cosine distance on StandardScaler-normalised taste features.
4. Aggregate thesis metrics below.

Taste features exclude sensory `Alcohol` and ABV (constraint axis only).

## Metrics

| Metric | Value |
|--------|------:|
| Constraint Satisfaction Rate | {pct(metrics["constraint_satisfaction_rate"])} |
| Recommendation pairs checked | {metrics["n_recommendation_pairs_checked"]} |
| Average Cosine Similarity | {num(metrics["average_cosine_similarity"])} |
| Average Taste Match % | {num(metrics["average_taste_match_pct"], 2)} |
| Average ABV Reduction (pp) | {num(metrics["average_abv_reduction"], 3)} |
| Average ABV Reduction % | {num(metrics["average_abv_reduction_pct"], 2)} |
| Average alcohol_ml Reduction | {num(metrics["average_alcohol_ml_reduction"], 3)} |
| Average alcohol_ml Reduction % | {num(metrics["average_alcohol_ml_reduction_pct"], 2)} |
| Recommendation Coverage | {pct(metrics["recommendation_coverage"])} |
| No-Recommendation Rate | {pct(metrics["no_recommendation_rate"])} |
| Products with ≥1 recommendation | {metrics["n_with_at_least_one_recommendation"]} |
| Products with 0 recommendations | {metrics["n_with_no_recommendation"]} |
| Self-recommendations (should be 0) | {metrics["self_recommendation_count"]} |

## No-recommendation reasons

| Reason | Count |
|--------|------:|
{reason_lines}

## Interpretation notes

- With uniform default `serving_ml = 375`, alcohol_ml reductions track ABV reductions.
- Constraint satisfaction should be ~100% by construction of the filter.
- Lowest-alcohol products naturally drive the no-recommendation rate.
- Machine-readable copy: `reports/offline_evaluation.json`.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> None:
    model = SipMateRecommender.load(MODELS_DIR)
    metrics = evaluate(model, top_k=DEFAULT_TOP_K)
    REPORT_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_markdown(metrics)

    print("Offline evaluation complete")
    print(f"  coverage: {metrics['recommendation_coverage']:.4f}")
    print(f"  no-rec rate: {metrics['no_recommendation_rate']:.4f}")
    print(f"  constraint sat: {metrics['constraint_satisfaction_rate']}")
    print(f"  avg cosine sim: {metrics['average_cosine_similarity']}")
    print(f"  wrote: {REPORT_MD}")
    print(f"  wrote: {REPORT_JSON}")


if __name__ == "__main__":
    main()
