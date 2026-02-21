# Task 06: Write unit tests

| Field | Value |
|-------|-------|
| **Owner** | Tech-QA |
| **Depends on** | 02, 03 |
| **Status** | Done |
| **Started** | 2026-02-21 00:22 |
| **Completed** | 2026-02-21 00:22 |
| **Duration** | < 1m |

## Goal

Write comprehensive unit tests covering each ecosystem's test detection, classification, mapping, and counting.

## Inputs

- `src/repo_mirror_kit/harvester/analyzers/test_patterns.py`
- `tests/unit/test_route_analyzer.py` (pattern reference)

## Definition of Done

- [x] Tests for Jest/Vitest detection and counting
- [x] Tests for pytest detection and counting
- [x] Tests for Go test detection and counting
- [x] Tests for .NET test detection (xUnit, NUnit, MSTest)
- [x] Tests for Cypress/Playwright e2e detection
- [x] Tests for test type classification
- [x] Tests for test-to-source file mapping (all ecosystems)
- [x] Tests for config framework detection
- [x] Tests for TestPatternSurface dataclass
- [x] Integration test with mixed ecosystems