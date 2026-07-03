# BEAN-062: API Contract Extraction — Python (Tracer Bullet)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-062 |
| **Status** | Done |
| **Priority** | Critical |
| **Created** | 2026-07-03 |
| **Completed** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

`ApiSurface.request_schema` and `response_schema` (`surfaces.py:121-122`) are defined but **never populated by any analyzer** — every API bean ships with empty contracts. A rebuild agent gets `POST /api/orders` with no idea what goes in or comes out. This is the single most damaging gap for the functional-replacement goal. Python stacks are the tracer bullet because stdlib `ast` means no new dependencies.

## Goal

For Flask and FastAPI endpoints, `request_schema` and `response_schema` are populated as JSON-Schema-shaped dicts, extracted via stdlib `ast`.

## Scope

### In Scope
- FastAPI: Pydantic model parameters → request schema; `response_model=` / return annotations → response schema; path/query params with types
- Flask: `request.json`/`request.form`/`request.args` key accesses → inferred request fields; `jsonify(...)`/returned-dict literals → inferred response fields; marshmallow schemas where present
- Resolve Pydantic/marshmallow model classes defined in other files within the repo (single-hop import following)
- Populate `ApiSurface.request_schema` / `response_schema` with a consistent JSON-Schema-ish structure: `{"fields": [{"name", "type", "required", "source"}]}` plus a `confidence` marker (`declared` vs `inferred`)
- Extend the `python-flask` fixture with a schema-rich endpoint; unit + integration assertions on populated contracts
- API bean template renders the contract tables instead of omitting them

### Out of Scope
- JS/TS stacks (BEAN-063), .NET (follow-up after 063)
- OpenAPI document generation (BEAN-071 consumes this)
- Response status-code branching beyond the happy path (record primary shape; note alternates as gaps)

## Acceptance Criteria

- [x] Harvesting the `python-flask` fixture yields ≥1 API surface with non-empty `request_schema` AND `response_schema`
- [x] FastAPI Pydantic-based endpoints produce field name/type/required triples matching the model definition
- [x] Un-inferable shapes produce an explicit `{"unknown": true}` marker, never a silently empty dict
- [x] API bean markdown shows request/response field tables
- [x] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A — **recommended first slice** together with BEAN-071 + BEAN-076
- Wave 1 — no dependencies (stdlib `ast`, not tree-sitter)
- Touches `surfaces.py` semantics only additively (populating existing fields + optional `confidence`)

## Implementation Notes (Tech-QA)

- New `analyzers/api_contracts.py`: `populate_python_api_contracts()` — stdlib-`ast` extraction, FastAPI (declared) + Flask (inferred), single-hop import resolution, per-file parse cache. 12 unit tests.
- Bean template renders field tables via `_render_contract_schema()`; `{"unknown": true}` renders as a visible gap note.
- **Bonus fix 1 (critical):** the detector registry was EMPTY in all production pipeline runs — nothing in `src/` imported the concrete detector modules, so stack detection always returned `{}` and stack-gated analyzers (APIs/components/models) never ran outside unit tests. Fixed by importing all detector modules in `detectors/__init__.py`.
- **Bonus fix 2:** Python API detection was path-shape-only (undetectable minimal apps). Added dependency-manifest content signal (`requirements.txt`/`pyproject.toml` declaring flask/fastapi, +0.6 confidence); `InventoryResult` now carries `workdir` so detectors can read manifests.
- Fixture upgraded (email field, richer response); e2e asserts populated field tables for `POST /api/users`.
