# BEAN-077: Golden Parity Fixtures (Request/Response Captures)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-077 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Parity scoring (BEAN-078) needs ground truth: what does the *original* app actually respond, given known requests and known state? The fixture apps (`python-flask`, `ts-next`) are runnable, but nothing captures their observable behavior as replayable goldens, and the fixtures are currently too thin to exercise interesting behavior (rules, workflows, lookups).

## Goal

Both fixture apps enriched to exercise Track A features (forms with validation, a status workflow, a lookup table, auth), plus a capture harness that runs each fixture and records golden request/response pairs (and resulting DB state snapshots) to `tests/fixtures/goldens/`.

## Scope

### In Scope
- Fixture enrichment: `python-flask` and `ts-next` each gain a form with validation rules, an entity with a status workflow, a seeded lookup table, and an auth-protected endpoint (coordinate with BEAN-062–067 fixture needs — one shared enrichment, not seven conflicting ones)
- `tests/parity/capture.py`: boots a fixture app, replays a scripted request sequence, records `{request, response, db_state_after}` JSON goldens (deterministic: fixed clock/ids where the apps allow)
- Golden format documented + versioned; regeneration command (`make goldens` or pytest marker)
- CI job (or marker) that verifies goldens still match the fixture apps (fixture drift detection)

### Out of Scope
- Capturing third-party apps (fixtures only)
- UI-interaction capture (API-level goldens v1; screens verified via Gherkin in BEAN-078)

## Acceptance Criteria

- [ ] Both fixtures boot via the capture harness and produce goldens covering happy path + ≥1 validation rejection + ≥1 auth rejection + ≥1 workflow transition each
- [ ] Goldens are deterministic across two consecutive capture runs
- [ ] A deliberate fixture behavior change makes golden verification fail (negative test)
- [ ] Golden format documented for BEAN-078 consumption
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track D
- Wave 1 — no hard deps, but **do this early**: richer fixtures are what every Track A bean tests against. Coordinate fixture additions across 062–067 through this bean
