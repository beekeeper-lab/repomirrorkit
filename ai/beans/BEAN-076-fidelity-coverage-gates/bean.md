# BEAN-076: Fidelity Coverage Gates (Recreation-Readiness Metrics)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-076 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Current coverage gates cannot fail by construction: every surface always gets a bean, and empty categories pass vacuously — they verify plumbing, not analysis quality. They say nothing about whether the output could recreate the app. As Track A lands richer extraction, gates must measure *recreation-readiness*, or regressions in fidelity will be invisible.

## Goal

A second gate family ("fidelity gates") in Stage F measuring depth, not existence: % of API surfaces with populated contracts, % of screen fields with model bindings, % of models with relationship details, % of beans without TODO placeholders, gap counts per category — reported in `coverage.{md,json}` and enforceable via `--fail-on-fidelity`.

## Scope

### In Scope
- `reports/fidelity.py`: metric computation over surfaces + beans (contract-populated %, field-mapping %, relationship %, enum-values %, placeholder-free %, per-category gap totals)
- Configurable thresholds with sane defaults; explicit vacuous-pass reporting (a category with 0 surfaces is *reported* as N/A, not silently passed)
- `--fail-on-fidelity` CLI flag (mirrors `--fail-on-gaps`); exit-code behavior tested
- Metrics emitted into `coverage.json` under a `fidelity` key + rendered section in `coverage.md`
- Fixture-based regression tests pinning expected fixture scores (updated deliberately as extraction improves)

### Out of Scope
- Behavioral parity measurement (BEAN-078 — different beast: requires a rebuild)
- Redefining the existing existence gates (kept as-is)

## Acceptance Criteria

- [ ] Fidelity metrics appear in `coverage.md`/`.json` for fixture harvests
- [ ] Before BEAN-062 lands, contract-populated % is honestly ~0 for fixtures (proves the gate isn't vacuous); after, it rises — CI pins both expectations at their respective times
- [ ] `--fail-on-fidelity` exits non-zero when a threshold is missed
- [ ] N/A categories are visibly distinct from 100% categories
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track D
- Wave 1–2 — no hard deps (metrics of empty data are honest zeros); part of the recommended first slice (062 → 071 → 076)
- These scores become the per-run "how recreation-ready is this harvest?" headline number
