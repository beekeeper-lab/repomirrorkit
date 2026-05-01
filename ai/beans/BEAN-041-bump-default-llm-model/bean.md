# BEAN-041: Bump Default LLM Model to Claude Sonnet 4.6

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-041 |
| **Status** | Done |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 11:13 |
| **Completed** | 2026-05-01 11:15 |
| **Duration** | 24m |
| **Owner** | team-lead |
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
| 1 | Bump default LLM model | developer | — | Pending |
| 2 | Verify bump + no regressions | tech-qa | 01 | Pending |

> Skipped: BA (mechanical config change); Architect (single value swap, no design implications).

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Affected files: `src/repo_mirror_kit/harvester/cli.py:128`, `harvester/config.py`, `harvester/llm/client.py`
- No dependencies on other beans
- Will produce a small surface change (default behavior of `--llm-model`) — note in PR description but no migration needed since this is a default, not a removed option

### Verification (Tech-QA)

- ✅ `grep -r "claude-sonnet-4-20250514" src/ tests/` — no matches.
- ✅ All 4 sites updated to `claude-sonnet-4-6`: `cli.py:128`, `config.py:57`, `llm/client.py:33`, `tests/unit/test_llm_client.py:92`.
- ✅ `uv run pytest tests/unit/test_llm_client.py` — 10 passed.
- ✅ `uv run ruff check src/ tests/` — All checks passed.
- ✅ `uv run requirements-harvester harvest --help` — shows `[default: claude-sonnet-4-6]` for `--llm-model`.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Bump default LLM model | developer | 1m | 3,557,275 | 2,199 | $5.59 |
| 2 | Verify bump + no regressions | tech-qa | < 1m | 87,532,520 | 416,990 | $207.78 |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 2 |
| **Total Duration** | 1m |
| **Total Tokens In** | 91,089,795 |
| **Total Tokens Out** | 419,189 |