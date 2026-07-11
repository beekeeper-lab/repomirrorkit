# Task 01 — Developer: exact-value extraction + LLM contract

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Depends On** | BEAN-081 (enrichment contract) |
| **Status** | In Progress |
| **Started** | 2026-07-11 12:16 |
| **Completed** | — |
| **Duration** | — |

## Goal

Populate the `exact_rules` / `error_contract` / `token_session` enrichment
keys that BEAN-081's tables render, from (a) structural analyzers (Flask/
FastAPI error responses; SQLAlchemy defaults/enums/checks/not-null/unique)
and (b) the LLM enrichment response. Route all captured literals through a
single chokepoint (`sanitize_captured_literal`) that BEAN-083 will wrap.

## Inputs

- `analyzers/api_contracts.py`, `analyzers/models/sqlalchemy.py`, `_common.py`
- `llm/prompts.py`, `llm/enrichment.py`
- `beans/templates.py` (contract: `_render_exact_rules_table`,
  `_render_error_contract_table`)
- fixture `tests/fixtures/sample-projects/python-flask`

## Definition of Done

- [ ] Enrichment keys populated with confidence ladder; verbatim values, no code blocks.
- [ ] Chokepoint seam in place + test.
- [ ] LLM prompt requires exact quoting / forbids code blocks; parser stores + strips fences.
- [ ] Fixture beans render real validation/error tables; suite + lint + mypy clean.
