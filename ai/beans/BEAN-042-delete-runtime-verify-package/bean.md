# BEAN-042: Delete Vestigial `runtime_verify` Package

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-042 |
| **Status** | Approved |
| **Priority** | Low |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The package `src/repo_mirror_kit/harvester/runtime_verify/` exists but is empty: the only file is `__init__.py` containing a single `from __future__ import annotations` import and nothing else. No code anywhere in the repository imports from this package. It appears to be either a placeholder for an abandoned feature or a stub that was never filled in. Empty packages are a source of confusion: they imply functionality that does not exist, they show up in import graphs and tab-completion, and they bloat the directory tree without earning their place.

## Goal

The empty `runtime_verify/` package is removed from the codebase. Either it is deleted entirely (decision recorded in this bean's notes), or — if there is a real intent for runtime verification — a brief design stub is filed as a separate bean and this bean is closed in favor of that one.

## Scope

### In Scope
- Confirm no imports of `runtime_verify` exist anywhere in `src/`, `tests/`, or scripts (`grep -r "runtime_verify" .`)
- Delete `src/repo_mirror_kit/harvester/runtime_verify/` directory
- Add a one-line note to `REVIEW_NOTES.md` (or this bean's notes) recording that the directory was intentionally removed

### Out of Scope
- Designing or implementing actual runtime verification functionality (separate bean if needed)
- Touching any other vestigial directories — single-purpose cleanup

## Acceptance Criteria

- [ ] `grep -r "runtime_verify" src/ tests/` returns no matches
- [ ] `src/repo_mirror_kit/harvester/runtime_verify/` no longer exists on disk
- [ ] All existing tests pass (`uv run pytest`)
- [ ] Lint and type-check clean (`uv run ruff check`, `uv run mypy src/`)
- [ ] Removal is recorded in commit message and bean notes

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Dead code / vestigial pieces" (2026-05-01)
- Verification done at review time: directory contains only `__init__.py` (35 bytes), no other files, no imports anywhere in tree
- No dependencies on other beans

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 |      |       |          |           |            |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
