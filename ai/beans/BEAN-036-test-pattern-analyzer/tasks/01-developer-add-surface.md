# Task 01: Add TestPatternSurface to surfaces.py and extend SurfaceCollection

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends on** | — |
| **Status** | Done |
| **Started** | 2026-02-21 00:22 |
| **Completed** | 2026-02-21 00:22 |
| **Duration** | < 1m |

## Goal

Add `TestPatternSurface` dataclass with test-specific fields and extend `SurfaceCollection` to include `test_patterns` list.

## Inputs

- `src/repo_mirror_kit/harvester/analyzers/surfaces.py`

## Definition of Done

- [x] `TestPatternSurface` dataclass exists with test_type, framework, test_file, subject_file, test_count, test_names fields
- [x] `SurfaceCollection.test_patterns` list field exists
- [x] `__iter__`, `__len__`, `to_dict` updated to include test_patterns