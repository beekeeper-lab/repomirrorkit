# BEAN-041 Task 01: Bump Default LLM Model

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Status** | Done |
| **Started** | 2026-05-01 11:14 |
| **Completed** | 2026-05-01 11:15 |
| **Duration** | 1m |
| **Depends On** | — |

## Goal

Replace the hard-coded default `claude-sonnet-4-20250514` (Sonnet 4.0) with `claude-sonnet-4-6` (Sonnet 4.6) at every site, plus update the one test assertion that pins the old default.

## Inputs

- `src/repo_mirror_kit/harvester/cli.py:128`
- `src/repo_mirror_kit/harvester/config.py:57`
- `src/repo_mirror_kit/harvester/llm/client.py:33`
- `tests/unit/test_llm_client.py:92`

## Acceptance Criteria

- [ ] `grep -r "claude-sonnet-4-20250514" src/ tests/` returns no matches
- [ ] All four sites use `claude-sonnet-4-6`
- [ ] `uv run pytest tests/unit/test_llm_client.py` passes
- [ ] CLI help text shows `claude-sonnet-4-6` as the default

## Definition of Done

- All AC met
- Changes committed on the feature branch
