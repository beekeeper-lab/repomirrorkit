# BEAN-082: Exact-Value Extraction — Analyzer Depth + LLM `exact_rules` Contract

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-082 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-07-11 |
| **Started** | 2026-07-11 12:15 |
| **Completed** | 2026-07-11 12:33 |
| **Duration** | 19m |
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

- [x] Fixture Flask/FastAPI endpoints emit error contracts: condition, exact status code, exact detail/message string. *(live: `| user is None | 404 | User not found | inferred |`)*
- [x] Fixture SQLAlchemy models emit defaults, enum members, and check constraints as exact values. *(live: NOT NULL, `admin\|member\|guest`, default `"member"`, `length(name) > 0`)*
- [x] Enrichment responses include populated `exact_rules` on fixture runs; parser rejects/strips code blocks from LLM output. *(recursive fence stripping; Tech-QA probe confirmed)*
- [x] All captured literals pass through one chokepoint function (the BEAN-083 seam) — verified by test. *(`sanitize_captured_literal`; monkeypatch test over all 6 value paths)*
- [x] Confidence ladder (BEAN-070: declared > inferred > llm > structural) applied to every new datum.
- [x] All tests pass *(1909 passed)*
- [x] Lint clean *(ruff + mypy src clean)*

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Developer: exact-value extraction + LLM contract | developer | BEAN-081 | Done |
| 2 | Tech-QA: independent verification (PASS) | tech-qa | 1 | Done |

## Notes

- Spec: `SPEC-MIRROR-MODE.md` Phase 2 (M2.3–M2.4).
- Python-first by design (mirrors BEAN-062 tracer-bullet approach); JS/TS parity arrives with BEAN-061/063.
- Implemented by delegated Developer agent; independently verified by a fresh
  Tech-QA agent (live fixture harvest + adversarial AST/chokepoint probes).
- **Carry-forward to BEAN-083 (Tech-QA finding L1):** the API `condition`
  descriptor is derived via `ast.unparse(node.test)` in `api_contracts.py` and
  does NOT pass through `sanitize_captured_literal`. A secret/PII literal inside
  an `if` guard (e.g. `if token == "abc123":`) would surface in the rendered
  Condition cell, bypassing redaction. BEAN-083 must route condition
  descriptors through the chokepoint too, or redact them at render time.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Developer: exact-value extraction + LLM contract | developer | — | — | — | — |
| 2 | Tech-QA: independent verification (PASS) | tech-qa | < 1m | 124,274,641 | 650,705 | $321.18 |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 1 |
| **Total Duration** | 19m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |