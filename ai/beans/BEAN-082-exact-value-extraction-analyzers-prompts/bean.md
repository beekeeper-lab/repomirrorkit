# BEAN-082: Exact-Value Extraction — Analyzer Depth + LLM `exact_rules` Contract

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-082 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-07-11 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The verbatim-rule tables (BEAN-081) need exact data to render, and today nothing produces it. API contract extraction (`analyzers/api_contracts.py`, BEAN-062) captures field name/type/required but **no error responses, status codes, validation rules, or examples**; model analyzers capture PK/not-null/unique but **no defaults, enum values, or check constraints**; and the LLM enrichment prompt (`llm/prompts.py`) neither requires exact quoting nor forbids code blocks, so enriched descriptions paraphrase rules instead of preserving them. Paraphrased rules break functional parity across rebuilds.

Full design: `SPEC-MIRROR-MODE.md` Phase 2 (M2.3, M2.4), decision D1.

## Goal

Analyzers and enrichment produce exact, framework-neutral rule data — error contracts, status codes, defaults, enums, constraints, and an `exact_rules` enrichment field — that BEAN-081's templates render, closing the paraphrase gap between original and rebuilt behavior.

## Scope

### In Scope
- `analyzers/api_contracts.py`: capture error responses and status codes — Flask `abort(code)`, returned status tuples; FastAPI `HTTPException(status_code=…, detail=…)`, `status_code=` decorators.
- Model analyzers (`analyzers/models/`): column defaults, enum column types/members, check constraints, indexes (SQLAlchemy first, matching existing per-framework split from BEAN-057).
- `llm/prompts.py` + `llm/enrichment.py`: prompt contract requiring exact quoting of literals, forbidding code blocks, expressing algorithms as neutral expressions/given-when-then; new structured response field `exact_rules: [{subject, rule, value, error_message, source_ref}]`, parsed and stored on `surface.enrichment`.
- All captured literals route through the BEAN-083 sensitive-value filter **if it has landed**; otherwise a seam (single chokepoint function) is left where the filter plugs in.

### Out of Scope
- Template rendering (BEAN-081).
- Sensitive-value detection/redaction/reporting itself (BEAN-083).
- JS/TS extraction depth (BEAN-063/061 — tree-sitter track) and the general `BusinessRuleSurface` (BEAN-065; when it lands it adopts this same verbatim output contract).

## Acceptance Criteria

- [ ] Fixture Flask/FastAPI endpoints emit error contracts: condition, exact status code, exact detail/message string.
- [ ] Fixture SQLAlchemy models emit defaults, enum members, and check constraints as exact values.
- [ ] Enrichment responses include populated `exact_rules` on fixture runs; parser rejects/strips code blocks from LLM output (existing fenced-JSON stripping extended, `enrichment.py:158-193`).
- [ ] All captured literals pass through one chokepoint function (the BEAN-083 seam) — verified by test.
- [ ] Confidence ladder (BEAN-070: declared > inferred > llm > structural) applied to every new datum.
- [ ] All tests pass
- [ ] Lint clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Spec: `SPEC-MIRROR-MODE.md` Phase 2 (M2.3–M2.4).
- Python-first by design (mirrors BEAN-062 tracer-bullet approach); JS/TS parity arrives with BEAN-061/063.

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
