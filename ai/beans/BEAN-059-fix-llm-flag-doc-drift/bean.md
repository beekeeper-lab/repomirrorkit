# BEAN-059: Fix `--llm` Flag Doc Drift + Config Default Mismatch

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-059 |
| **Status** | Done |
| **Priority** | Low |
| **Created** | 2026-07-03 |
| **Completed** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Documentation and defaults drifted after BEAN-056: `README.md` (and root `CLAUDE.md`) still reference a `--llm-enabled` flag that no longer exists (the CLI now uses `--llm/--no-llm`, default on). Separately, `HarvestConfig.llm_enabled` defaults to `False` (`config.py`) while the CLI defaults to `True` — programmatic users of `HarvestConfig` silently get different behavior than CLI users.

## Goal

Docs match the CLI exactly; `HarvestConfig` and CLI defaults agree (single source of truth for the default).

## Scope

### In Scope
- Update `README.md` and root `CLAUDE.md` references to `--llm/--no-llm` semantics
- Align `HarvestConfig.llm_enabled` default with the CLI default (or derive the CLI default from the dataclass)
- Audit `pyproject.toml` description and CLI `--help` text for the same drift

### Out of Scope
- Any behavioral change to enrichment itself

## Acceptance Criteria

- [x] No reference to `--llm-enabled` remains anywhere in the repo (grep clean)
- [x] `HarvestConfig()` constructed with no args produces the same LLM behavior as a bare CLI invocation
- [x] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), plumbing fixes
- Wave 1 — no dependencies; fully parallel with everything
