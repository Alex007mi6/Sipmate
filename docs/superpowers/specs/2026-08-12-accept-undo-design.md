# Accept Undo (multi-step ladder stack)

Date: 2026-08-12  
Status: implemented  
Approach: Frontend session stack + `LIGHTER_CHOICE_UNDONE` API

## Behavior

- After Accept, push `{ fromProductId, toProductId }` onto a per-`session_id` stack in `sessionStorage`.
- Undo pops one step, calls undo API, navigates to `fromProductId`.
- Stack can unwind to the original drink; unlimited time within the browser session.
- Selecting a drink on Drinks clears the stack (new round).
- Top-left Back to Drinks does not auto-undo.

## API

`POST /api/gamification/events` with `event_type: LIGHTER_CHOICE_UNDONE`  
Body: `selected_product_id` = from, `recommended_product_id` = to (same pair as Accept).

Server deletes award rows for that `reference_id` (`LIGHTER_CHOICE_ACCEPTED`, `ALCOHOL_FREE_CHOICE`), revokes badges that no longer meet thresholds, logs a recommendation undo event. Anonymous users: navigation-only success.

Response: `points_reversed`, `badges_revoked`, plus existing fields.

## UI

Recommend page shows **Undo** in the page head when stack non-empty. Feedback: `Undone` or `Undone · −N pts`.
