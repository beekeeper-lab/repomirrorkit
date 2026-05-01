# BEAN-041: Bump Default LLM Model to Claude Sonnet 4.6

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-041 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester's default LLM model is `claude-sonnet-4-20250514` (Sonnet 4.0, May 2025), hard-coded as the default for `--llm-model` (`src/repo_mirror_kit/harvester/cli.py:128`) and propagated through `HarvestConfig` and `harvester/llm/client.py`. As of today (2026-05-01) this model is approximately one year old. The current Claude Sonnet release is Sonnet 4.6 (`claude-sonnet-4-6`, ~April 2026), which has materially better instruction-following and reasoning quality — both directly relevant to LLM-driven enrichment of harvester surfaces. Continuing to ship the older default produces lower-quality requirement artifacts than the project is capable of, and signals stale tooling to users.

## Goal

Default LLM model across the harvester is `claude-sonnet-4-6`. Users running with default settings get the latest Sonnet output. The override path (`--llm-model` flag, env override, programmatic override) continues to work for users pinning to other model IDs.

## Scope

### In Scope
- Update default model ID in `src/repo_mirror_kit/harvester/cli.py` (`--llm-model` default)
- Update default in `src/repo_mirror_kit/harvester/config.py` (`HarvestConfig.llm_model` default)
- Update default and any inline comment/help in `src/repo_mirror_kit/harvester/llm/client.py`
- Update any test fixture / docstring that hard-codes the old model ID, where doing so does not change test intent
- Run a manual smoke test against a small fixture repo with `--llm-enabled` to confirm no breakage

### Out of Scope
- Changing the model used by Claude Code itself (this bean targets only the harvester's internal LLM enrichment)
- Migrating to Opus or Haiku
- Restructuring how the model is configured (env vs flag vs config) — that's a separate concern

## Acceptance Criteria

- [ ] `grep -r "claude-sonnet-4-20250514" src/ tests/` returns no matches
- [ ] CLI help text (`uv run requirements-harvester harvest --help`) shows `claude-sonnet-4-6` as the default
- [ ] `HarvestConfig` constructed with no explicit `llm_model` returns `claude-sonnet-4-6`
- [ ] All existing unit tests pass (`uv run pytest`)
- [ ] Lint and type-check clean (`uv run ruff check`, `uv run mypy src/`)
- [ ] Manual smoke test with `--llm-enabled` against a small public repo completes successfully

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Affected files: `src/repo_mirror_kit/harvester/cli.py:128`, `harvester/config.py`, `harvester/llm/client.py`
- No dependencies on other beans
- Will produce a small surface change (default behavior of `--llm-model`) — note in PR description but no migration needed since this is a default, not a removed option

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
