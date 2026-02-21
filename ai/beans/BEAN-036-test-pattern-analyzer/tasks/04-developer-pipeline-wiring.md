# Task 04: Wire analyzer into pipeline Stage C

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends on** | 02 |
| **Status** | Done |
| **Started** | 2026-02-21 00:22 |
| **Completed** | 2026-02-21 00:22 |
| **Duration** | < 1m |

## Goal

Import and call `analyze_test_patterns` in the pipeline Stage C, update `__init__.py` exports.

## Inputs

- `src/repo_mirror_kit/harvester/pipeline.py`
- `src/repo_mirror_kit/harvester/analyzers/__init__.py`

## Definition of Done

- [x] `analyze_test_patterns` imported in `__init__.py` and `pipeline.py`
- [x] `TestPatternSurface` exported from `__init__.py`
- [x] Analyzer called in `_run_stage_c()` with progress emission
- [x] `test_patterns` passed to `SurfaceCollection` constructor