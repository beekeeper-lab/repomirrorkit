# Task 02: Verify clone form window

| Field | Value |
|-------|-------|
| **Owner** | Tech-QA |
| **Status** | Done |
| **Depends On** | Task 01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Independently verify all 15 acceptance criteria from BEAN-002. Run all tooling commands, review test coverage, and confirm the clone form works correctly.

## Inputs

- BEAN-002 `bean.md` (acceptance criteria)
- All files created by Task 01

## Verification Checklist

- [ ] User can type a project name and git URL into labeled text fields
- [ ] Clicking Fetch with empty project name shows inline validation error, no clone starts
- [ ] Clicking Fetch with empty URL shows inline validation error, no clone starts
- [ ] Clicking Fetch with valid inputs clones the repository to `./projects/<project-name>/`
- [ ] `./projects/` directory is created automatically if it does not exist
- [ ] Fetch button is disabled while clone is in progress
- [ ] Status label updates to "Cloning..." when clone starts
- [ ] Git clone output appears in log area in real time
- [ ] On success, status shows "Clone complete" and button re-enables
- [ ] On failure, status shows error and button re-enables
- [ ] UI remains responsive during clone (no freezing)
- [ ] Non-GitHub URLs work (any git remote)
- [ ] If target directory exists, clone fails gracefully with error message
- [ ] All new code has unit tests; clone worker and service tested
- [ ] `uv run ruff check src/ tests/` — zero issues
- [ ] `uv run ruff format --check src/ tests/` — no changes needed
- [ ] `uv run mypy src/` — zero errors in strict mode
- [ ] `uv run pytest tests/` — all tests pass
- [ ] All new .py files have `from __future__ import annotations`
- [ ] No hardcoded secrets, credentials, or environment-specific values

## Definition of Done

All 20 checklist items pass. Any failures reported with specific details.
