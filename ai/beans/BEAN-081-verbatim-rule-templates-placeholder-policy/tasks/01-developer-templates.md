# Task 01 — Developer: verbatim-rule templates + zero-TODO policy

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Depends On** | — |
| **Status** | Done |
| **Started** | 2026-07-11 12:07 |
| **Completed** | 2026-07-11 12:07 |
| **Duration** | < 1m |

## Goal

Eliminate every literal `TODO:` from generated beans; render exact-value
validation/error tables when data exists; declare all unknowns as gaps.

## Inputs

- `src/repo_mirror_kit/harvester/beans/templates.py`
- `SPEC-MIRROR-MODE.md` Phase 2 (M2.1, M2.2)

## Acceptance Criteria / Definition of Done

- [x] `derive_confidence_and_gaps` is the single gap authority; adds behavioral,
      GWT, data-flow, and contract-level gaps (validation, errors, token/session,
      description, module purpose) matched to each renderer.
- [x] `_UNDETERMINED` / `_NONE_IDENTIFIED` markers replace all 14 `TODO:` sites.
- [x] `_render_exact_rules_table` (reads `enrichment["exact_rules"]`) and
      `_render_error_contract_table` (reads `enrichment["error_contract"]`) render
      verbatim value tables; degrade to a gap marker when absent. Contract shapes
      documented in docstrings for BEAN-082.
- [x] `token_session` enrichment renders in the auth bean.
- [x] No source-code blocks emitted for rule data.
