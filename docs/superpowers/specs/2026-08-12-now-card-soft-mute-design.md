# Soft-mute NOW card (Lighter picks)

Date: 2026-08-12  
Status: implemented

## Goal

On the recommend (“Lighter picks”) page, visually de-emphasize the current drink (**NOW**) so it reads as a less desirable baseline, and push attention toward the recommendation cards (**NEXT**) and their Accept CTA—without shame-style red warning UI.

## Chosen approach

**A · Soft mute**

- NOW: desaturated gray-green surface; muted chip and type.
- NEXT: keep existing bright white / brand-green bordered cards (`.drink-block.alt`) and gold Accept button.

## Visual spec

### NOW (`.drink-block.now` or equivalent)

| Token | Value |
|-------|--------|
| Background | `#d8e0db` |
| Border | `1px solid #b7c4bc` |
| Title / strong metrics | `#3a4a42` |
| Meta / secondary | `#6a7a72` |
| Chip background | `#c5cfc8` |
| Chip text | `#3a4a42` |
| Shadow | none or softer than NEXT (optional `0 4px 12px rgba(20,36,30,0.04)`) |

Metric tiles inside NOW should use a slightly darker wash than the card body (e.g. `rgba(20,36,30,0.06)`) so they remain readable but not “premium white”.

### NEXT (unchanged intent)

- Keep `.drink-block.alt`: white → `#f2f8f4` gradient, `2px` brand-green border.
- Keep bright green chip and gold `.btn-accent` Accept.

### Hierarchy rule

At a glance, NEXT cards must feel more elevated and actionable than NOW. Contrast comes from saturation and border weight, not from warning red/orange.

## Out of scope

- Changing recommendation copy, Accept/Ladder behavior, or alcohol units (already g / glass).
- Warm-caution (amber) NOW styling, recessed strip layout, or red “heavy” badges.
- Ladder page restyle (unless the same NOW pattern appears there later).

## Implementation notes

- `frontend/src/pages/RecommendPage.tsx`: mark the selected block with a dedicated class (e.g. `drink-block now`); keep recommendation cards on `drink-block alt`.
- `frontend/src/index.css`: add `.drink-block.now` (+ chip override if needed); do not weaken `.drink-block.alt`.
- No API or backend changes.

## Success criteria

1. NOW and NEXT are clearly different tones on first glance.
2. Eye path lands on NEXT / Accept before lingering on NOW.
3. NOW feels muted/heavier-as-baseline, not alarming or shaming.
