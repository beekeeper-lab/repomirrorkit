# BEAN-056: LLM Enrichment Default-On with Graceful Missing-Key UX

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-056 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

Today, `--llm-enabled` defaults to `False` (`src/repo_mirror_kit/harvester/cli.py:115`). The result is that the **default** harvest run produces beans full of literal "TODO: Describe the expected behavior..." placeholders (`harvester/beans/templates.py:117`) — that is, the default user experience is the *worst* user experience the tool offers. Users who don't know about the flag get the broken-looking output and conclude the harvester doesn't work. After BEAN-054 (behavioral analyzer) lands, structural-only mode becomes useful in its own right, but LLM enrichment is still where the highest-quality output comes from. Default-on is the right posture, provided the missing-key case is handled gracefully — which BEAN-045 prepares for by adding a clear, actionable error message when `ANTHROPIC_API_KEY` is missing.

## Goal

`--llm-enabled` defaults to `True`. When the API key is missing, the harvester emits a single clear warning explaining the trade-off and falls back to structural-only mode (rather than failing). Power users can opt out with an explicit `--no-llm`. The default end-to-end UX matches the project's stated goal: real requirements out of the box.

## Scope

### In Scope
- Flip the default of `--llm-enabled` to `True` in `harvester/cli.py`
- Rename the flag to a `--llm/--no-llm` toggle (Click idiom) for clarity
- When `--llm` is active and `ANTHROPIC_API_KEY` is absent, do **not** raise an error — instead emit a prominent, multi-line warning to stderr that:
  - Confirms the harvester is falling back to "structural-only mode"
  - Shows where to obtain a key (`https://console.anthropic.com/settings/keys`)
  - Shows the exact `export ANTHROPIC_API_KEY=…` command to enable LLM enrichment
  - Notes the user can suppress the warning with `--no-llm`
- Update `HarvestConfig` validation accordingly (BEAN-045 introduces the helper that this bean reuses)
- Update CLI help text and README usage examples
- Update existing test fixtures and tests that assume the old default
- Update integration test (BEAN-050) — current fixture tests should run with `--no-llm` to keep CI deterministic and offline; document this in test docstrings

### Out of Scope
- The actual missing-key error message wording — handled in BEAN-045
- Changing the default model — handled in BEAN-041
- Auto-detecting whether a project has LLM-relevant content (skip enrichment for tiny repos) — separate optimization

## Acceptance Criteria

- [ ] `requirements-harvester harvest --help` shows LLM enrichment as default-on
- [ ] Running with no flags and no API key produces a clear stderr warning AND completes successfully in structural-only mode
- [ ] Running with `--no-llm` produces no warning and completes in structural-only mode
- [ ] Running with `--llm` and a valid key produces enriched beans
- [ ] Existing tests are updated to opt out of LLM enrichment explicitly (`--no-llm` or programmatic equivalent)
- [ ] Integration tests run offline / no-API-key by passing `--no-llm`
- [ ] Lint, type-check, and pytest all clean
- [ ] Manual smoke test: `requirements-harvester harvest --repo …` (no flags, no key) runs to completion with the warning visible

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 2 (2026-05-01)
- **Depends on BEAN-045** — the missing-key error helper added in BEAN-045 is reused here as a warning helper. BEAN-045 must land first, otherwise this bean's "graceful fallback" has nothing to fall back to.
- Soft-coupled to BEAN-054: once both land, the structural-only fallback is genuinely useful (real behavioral signal from docstrings/tests), not just a degraded experience. Recommend landing BEAN-054 before BEAN-056 to make the fallback path good
- BA review on the warning message wording

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
