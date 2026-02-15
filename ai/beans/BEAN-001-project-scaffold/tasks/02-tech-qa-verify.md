# Task 02: Verify project scaffold

| Field | Value |
|-------|-------|
| **Owner** | Tech-QA |
| **Status** | Done |
| **Depends On** | Task 01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Independently verify all 9 acceptance criteria from BEAN-001. Run all tooling commands and confirm results.

## Inputs

- BEAN-001 `bean.md` (acceptance criteria)
- All files created by Task 01

## Verification Checklist

- [ ] `uv venv` creates working virtual environment
- [ ] `uv pip install -e ".[dev]"` installs without errors
- [ ] `python -m repo_mirror_kit` launches a window titled "RepoMirrorKit" (verify programmatically or via test)
- [ ] `uv run ruff check src/ tests/` — zero issues
- [ ] `uv run ruff format --check src/ tests/` — no changes needed
- [ ] `uv run mypy src/` — zero errors in strict mode
- [ ] `uv run pytest tests/` — passes with at least one smoke test
- [ ] All .py files have `from __future__ import annotations`
- [ ] No hardcoded secrets, credentials, or environment-specific values
- [ ] Project uses `src/` layout correctly

## Definition of Done

All 10 checklist items pass. Any failures reported with specific details.
