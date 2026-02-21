# Task 02: Implement test_patterns.py analyzer

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends on** | 01 |
| **Status** | Done |
| **Started** | 2026-02-21 00:22 |
| **Completed** | 2026-02-21 00:22 |
| **Duration** | < 1m |

## Goal

Implement `analyze_test_patterns()` function detecting test files across JS/TS, Python, Go, .NET, and Ruby ecosystems.

## Inputs

- `src/repo_mirror_kit/harvester/analyzers/routes.py` (pattern reference)
- `src/repo_mirror_kit/harvester/analyzers/surfaces.py`
- `src/repo_mirror_kit/harvester/inventory.py`

## Definition of Done

- [x] Detects Jest/Vitest test files and extracts describe/it block names
- [x] Detects pytest test files and extracts test function names
- [x] Detects Go test files
- [x] Detects .NET test classes (xUnit, NUnit, MSTest)
- [x] Detects Cypress/Playwright e2e test files
- [x] Classifies tests as unit, integration, e2e, snapshot, performance
- [x] Maps test files to source files via naming conventions
- [x] Detects test configuration files and frameworks
- [x] Counts tests per file (regex-based)