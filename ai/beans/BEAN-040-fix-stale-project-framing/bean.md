# BEAN-040: Fix Stale Project Framing in Docs

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-040 |
| **Status** | Approved |
| **Priority** | Low |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The user-facing documentation describes RepoMirrorKit as a tool for mirroring git repositories — that framing is stale. The project is actually a **requirements harvester**: a CLI (and PySide6 GUI shell) that analyzes a Git repository and generates structured requirement artifacts (beans, coverage reports, a Claude Code project folder). New contributors and users currently encounter conflicting information: `README.md` and `pyproject.toml` describe a "git mirroring tool" while the only entry point that does real work is `requirements-harvester`. The root `CLAUDE.md` does not mention the harvester at all, despite it being the bulk of the codebase.

## Goal

The README, `pyproject.toml` description, and root `CLAUDE.md` accurately describe what RepoMirrorKit does today: a requirements harvester with both a CLI and a thin GUI launcher. A new contributor reading any of these files alone gets a correct mental model.

## Scope

### In Scope
- Rewrite `README.md` to lead with the harvester purpose, document the `requirements-harvester` CLI usage, and reposition the GUI as a quick-start launcher
- Update `pyproject.toml` `description` field to match
- Add a "Harvester" section to the root `CLAUDE.md` summarizing the pipeline and pointing at `src/repo_mirror_kit/harvester/`

### Out of Scope
- Adding a comprehensive harvester user guide (`docs/HARVESTER.md`) — separate follow-up
- Generating diagrams or pipeline flow charts
- Changing any code or behavior

## Acceptance Criteria

- [ ] `README.md` opens with a one-paragraph summary that matches the harvester goal (input: Git repo; output: requirement artifacts)
- [ ] `README.md` shows a working `requirements-harvester harvest --repo <url>` example
- [ ] `pyproject.toml` `description` no longer says "mirroring git repositories"
- [ ] Root `CLAUDE.md` has a "Harvester" section pointing at `src/repo_mirror_kit/harvester/cli.py` and `pipeline.py`
- [ ] `grep -r "mirroring git repositories" .` returns no matches outside this bean's notes
- [ ] No code or test changes are introduced
- [ ] Lint clean (`uv run ruff check`)

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Source: `REVIEW_NOTES.md` §"Documentation & metadata staleness" (2026-05-01)
- Affected files: `README.md`, `pyproject.toml:8`, `CLAUDE.md`
- No dependencies on other beans
- Quick win — likely a single doc-author task; no Tech-QA needed beyond lint

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
