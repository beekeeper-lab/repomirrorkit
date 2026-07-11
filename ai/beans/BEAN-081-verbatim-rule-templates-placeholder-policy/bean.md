# BEAN-081: Verbatim-Rule Bean Templates + Zero-`TODO:` Placeholder Policy

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-081 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-11 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

Mirror-grade beans must be exact enough that two independent rebuilds behave identically — a loosely described validation rule or error message diverges across stacks. Today the bean templates (`beans/templates.py`) leave `## Validation rules`, `## Errors`, `## Examples`, and `## Open questions` as hardcoded `TODO:` lines, which (a) gives implementing agents nothing exact to build from and (b) makes the `placeholder_free_beans` fidelity metric (`fidelity.py:160-169`) structurally unable to reach 100%, so it stays informational instead of gating.

Decision D1 (locked 2026-07-11): beans capture rules **verbatim but never as code** — exact regexes, thresholds, enum members, defaults, error-message strings, status codes, and formulas re-expressed as framework-neutral expressions. Full design: `SPEC-MIRROR-MODE.md` Phase 2 (M2.1, M2.2).

## Goal

Bean templates render structured, exact-rule tables from surface/enrichment data, and every section that would have emitted `TODO:` either renders real data or converts to a declared `gaps:` frontmatter entry + `## Gaps & unknowns` line — so mirror output contains zero literal `TODO:` and `placeholder_free_beans = 100%` becomes achievable and honest (absence is declared, not silent).

## Scope

### In Scope
- Verbatim policy documented (bean-workflow doc + templates docstrings): exact literals in structured fields, never pasted source statements/blocks; formulas as neutral expressions.
- `## Validation rules` → table: Field | Rule | Exact value/pattern | Error message | Confidence.
- `## Errors` → table: Condition | Status | Error body/message.
- TODO→gap conversion across all `_RENDERERS` in `beans/templates.py`; `gaps:` frontmatter (BEAN-070 fields) is the declared-absence channel.
- Render the `exact_rules` enrichment field (produced by BEAN-082) into the new tables; degrade gracefully when absent (gap entry, not `TODO:`).
- Test asserting zero literal `TODO:` in beans generated from fixtures when data or gaps are present.

### Out of Scope
- Analyzer/prompt changes that *produce* exact values (BEAN-082).
- Secret/PII redaction of captured literals (BEAN-083 — but templates must render its typed placeholders verbatim, e.g. `[REDACTED:email]`).
- Fidelity threshold changes (BEAN-076 amendment).

## Acceptance Criteria

- [ ] No literal `TODO:` in any bean generated from the `python-flask` and `ts-next` fixtures with LLM enabled; unknowns appear as `gaps:` frontmatter + visible `## Gaps & unknowns` entries.
- [ ] Validation-rule and error tables render exact values (pattern strings, status codes, messages) when data exists; no source-code blocks anywhere in bean bodies.
- [ ] `placeholder_free_beans` reaches 100% on fixture mirror runs.
- [ ] Structural-only (no-LLM) runs still produce valid beans — gaps declared, never `TODO:`.
- [ ] All tests pass
- [ ] Lint clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Spec: `SPEC-MIRROR-MODE.md` Phase 2 (M2.1–M2.2). Gaming risk (everything becomes a gap) is countered by contract-coverage gates — see spec §6.
- Pairs with BEAN-082 (data production) — can land first with graceful degradation.

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
