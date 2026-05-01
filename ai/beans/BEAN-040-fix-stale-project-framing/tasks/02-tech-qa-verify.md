# BEAN-040 Task 02: Tech-QA — Verify Doc Updates

| Field | Value |
|-------|-------|
| **Owner** | tech-qa |
| **Status** | Done |
| **Started** | 2026-05-01 11:17 |
| **Completed** | 2026-05-01 11:17 |
| **Duration** | < 1m |
| **Depends On** | 01 |

## Goal

Independently confirm the three documents accurately describe the harvester, the README's commands actually work, and no regressions are introduced.

## Acceptance Criteria

- [ ] README's `requirements-harvester harvest --help` example actually runs
- [ ] `pyproject.toml` description matches the new framing
- [ ] Root CLAUDE.md Harvester section is accurate
- [ ] `grep -r "mirroring git repositories" README.md pyproject.toml CLAUDE.md` empty
- [ ] `uv run pytest` and `uv run ruff check` still clean (no test/lint regressions from doc-only changes)

## Definition of Done

- All AC checked; verification appended to bean.md Notes.
