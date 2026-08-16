# Stop / Settle + Alcohol metric label

Date: 2026-08-16  
Status: implemented

## Metric label

On NEXT cards, third metric caption changes from `Less` to `Alcohol` (value remains `↓N%`).

## Stop / Settle

- NOW card always shows a commit CTA:
  - No accept in this round: `I'll take this` (secondary)
  - After ≥1 Accept (ladder stack non-empty): `Stop here` (primary)
- Navigates to `/settled/:productId` (summary confirmation card A).
- Summary: final drink, ABV + g/glass, alcohol ↓% vs round origin, points from this round’s Accepts.
- CTAs: Rewards, New drink (clears ladder stack).
- Round origin = first `fromProductId` in undo stack, else current product.
- Round points = sum of `pointsAwarded` stored on stack steps.
