# BEAN-040 Task 01: Fix Stale Project Framing in Docs

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Status** | Done |
| **Started** | 2026-05-01 11:16 |
| **Completed** | 2026-05-01 11:17 |
| **Duration** | 1m |
| **Depends On** | — |

## Goal

Rewrite `README.md`, update `pyproject.toml` description, and add a Harvester section to root `CLAUDE.md` so all three accurately describe what the project does today: a requirements harvester (CLI primary, GUI secondary).

## Inputs

- `README.md` (current content describes "git mirroring")
- `pyproject.toml:8` (description field)
- `CLAUDE.md` (no Harvester reference today)

## Acceptance Criteria

- [ ] `README.md` opens with a one-paragraph summary of the harvester goal
- [ ] `README.md` shows a working `requirements-harvester harvest --repo <url>` example
- [ ] `pyproject.toml` description no longer says "mirroring"
- [ ] Root `CLAUDE.md` has a Harvester section pointing at `src/repo_mirror_kit/harvester/cli.py` and `pipeline.py`
- [ ] `grep -r "mirroring git repositories" .` returns no matches outside REVIEW_NOTES.md and bean docs

## Definition of Done

- All AC met; changes committed on the feature branch.
