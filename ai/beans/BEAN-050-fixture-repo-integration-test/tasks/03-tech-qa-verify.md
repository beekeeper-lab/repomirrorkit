# BEAN-050 Task 03: Tech-QA — Verify All Acceptance Criteria

| Field | Value |
|-------|-------|
| **Owner** | tech-qa |
| **Status** | Done |
| **Started** | 2026-05-01 11:12 |
| **Completed** | 2026-05-01 11:12 |
| **Duration** | < 1m |
| **Depends On** | 01, 02 |

## Goal

Independently verify every Acceptance Criterion in BEAN-050 bean.md is met. Confirm the integration test runs deterministically, offline, in under 60 seconds, and exercises real pipeline behavior (not mocks). Confirm the ruff and pytest gates are clean across the full suite.

## Inputs

- BEAN-050 bean.md Acceptance Criteria
- Task 01 outputs (fixtures + integration test)
- Task 02 outputs (gate fixes)

## Acceptance Criteria

- [ ] Both fixture directories exist with the documented file structure
- [ ] `tests/integration/test_pipeline_e2e.py` and `conftest.py` exist
- [ ] `pyproject.toml` registers the `integration` marker
- [ ] `uv run pytest tests/integration/ -v` runs both tests and both pass; total wall time < 60 seconds
- [ ] `uv run pytest -m "not integration"` (unit-only) passes — the marker actually filters
- [ ] `uv run pytest` (everything) passes
- [ ] `uv run ruff check src/ tests/` exits 0
- [ ] `uv run mypy src/` passes (or, if pre-existing mypy issues exist, document them as out-of-scope without introducing new ones)
- [ ] No network access made by the integration tests (verify by running with no internet — or by inspection: no http(s)/ssh URLs are used; only local-path clone)
- [ ] Integration tests do NOT require `ANTHROPIC_API_KEY`

## Definition of Done

- All Acceptance Criteria checked off
- Verification findings appended to BEAN-050 bean.md under a `## Verification (Tech-QA)` subsection
- If any AC fails: file follow-up (do not silently skip), document the gap, leave bean In Progress

## Notes

- This task is the gate before merging BEAN-050 to test. If any criterion fails, the bean stays In Progress and the loop stops per `/long-run`'s error protocol.
- The wall-time budget (60 seconds) is the contract to `/long-run`'s downstream beans — every bean's Tech-QA pass runs the full suite, so this gate's speed compounds across the whole backlog.
