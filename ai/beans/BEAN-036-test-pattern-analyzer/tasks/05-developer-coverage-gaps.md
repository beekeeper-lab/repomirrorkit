# Task 05: Add coverage gate and gap query

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends on** | 01 |
| **Status** | Done |
| **Started** | 2026-02-21 00:22 |
| **Completed** | 2026-02-21 00:22 |
| **Duration** | < 1m |

## Goal

Add test pattern coverage metric (70% threshold) and gap query for uncovered test patterns.

## Inputs

- `src/repo_mirror_kit/harvester/reports/coverage.py`
- `src/repo_mirror_kit/harvester/reports/gaps.py`

## Definition of Done

- [x] `THRESHOLD_TEST_PATTERNS = 70.0` constant added
- [x] `test_patterns` MetricPair added to CoverageMetrics
- [x] `compute_metrics()` includes test_patterns counting
- [x] `evaluate_thresholds()` includes Test Patterns gate
- [x] Coverage markdown report includes test patterns row
- [x] `find_test_patterns_without_bean()` gap query implemented
- [x] Gap query wired into `run_all_gap_queries()`