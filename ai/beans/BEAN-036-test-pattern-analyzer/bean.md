# BEAN-036: Test Pattern Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-036 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-02-20 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester analyzes application code but ignores the test suite. Tests encode critical behavioral expectations — what the system is supposed to do, edge cases it handles, and quality standards it maintains. A developer recreating the app needs to know the testing strategy, frameworks used, and what behaviors are verified. Without test analysis, generated requirements miss the verification layer that defines "done."

## Goal

Implement a test pattern analyzer that identifies test files, extracts testing frameworks, test categories (unit/integration/e2e), test subjects (which modules/components are tested), and key assertion patterns, producing `TestPatternSurface` objects for bean generation.

## Scope

### In Scope
- New surface dataclass: `TestPatternSurface` with fields for test_type (unit/integration/e2e/snapshot), framework, test_file, subject_file, test_count, describe/it blocks or test function names
- Add `test_patterns` list to `SurfaceCollection`
- Implement `src/repo_mirror_kit/harvester/analyzers/test_patterns.py`
- Detect test files and frameworks:
  - **JavaScript/TypeScript**: Jest, Vitest, Mocha, Cypress, Playwright (*.test.ts, *.spec.ts, __tests__/, cypress/, e2e/)
  - **Python**: pytest, unittest (test_*.py, *_test.py, tests/, conftest.py)
  - **Go**: testing package (*_test.go)
  - **.NET**: xUnit, NUnit, MSTest (*Tests.cs, *.Tests/)
  - **Ruby**: RSpec, Minitest (*_spec.rb, spec/, *_test.rb)
- Classify tests: unit, integration, e2e, snapshot, performance
- Extract test subjects by mapping test files to source files via naming conventions and import analysis
- Detect test configuration: jest.config, pytest.ini/pyproject.toml [tool.pytest], .mocharc, playwright.config
- Count tests per file (describe/it blocks, test functions, [Test] attributes)
- Bean template renderer for test pattern beans
- Wire into pipeline Stage C
- Coverage gate and gap query
- Unit tests

### Out of Scope
- Running tests or measuring pass/fail status
- Code coverage measurement
- Test quality assessment (assertion density, mutation testing)
- Generating new tests
- Mocking/stubbing pattern analysis

## Acceptance Criteria

- [ ] `TestPatternSurface` dataclass exists with test_type, framework, test_file, subject_file, test_count fields
- [ ] `SurfaceCollection.test_patterns` list field exists
- [ ] Detects Jest/Vitest test files and extracts describe/it block names
- [ ] Detects pytest test files and extracts test function names
- [ ] Detects Go test files
- [ ] Detects .NET test classes
- [ ] Detects Cypress/Playwright e2e test files
- [ ] Classifies tests as unit, integration, e2e, or snapshot based on location and naming conventions
- [ ] Maps test files to source files via naming conventions (test_foo.py -> foo.py)
- [ ] Detects test configuration files and frameworks
- [ ] Counts tests per file (approximate, regex-based)
- [ ] Bean template renders test pattern beans with framework, type, subject, and test count
- [ ] Coverage gate checks test pattern coverage (threshold >= 70%)
- [ ] Gap query identifies test patterns without beans
- [ ] Unit tests cover each ecosystem's test detection
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Add TestPatternSurface to surfaces.py and extend SurfaceCollection | Developer | — | Pending |
| 2 | Implement test_patterns.py analyzer | Developer | 1 | Pending |
| 3 | Add bean template renderer for test patterns | Developer | 1 | Pending |
| 4 | Wire analyzer into pipeline Stage C | Developer | 2 | Pending |
| 5 | Add coverage gate and gap query | Developer | 1 | Pending |
| 6 | Write unit tests | Tech-QA | 2, 3 | Pending |
| 7 | Run lint, type-check, and test suite | Tech-QA | 4, 5, 6 | Pending |

## Notes

- Depends on BEAN-009 (file inventory), BEAN-010 (detector framework), BEAN-019 (surface data model).
- Test-to-source mapping uses heuristics (naming conventions, directory mirroring). It will not be 100% accurate — that's acceptable for requirements generation.
- Test count is approximate (regex-based counting of `def test_`, `it(`, `[Test]`, etc.) — not AST-based.
- LLM enrichment (Stage C2) can read test files and generate behavioral descriptions of what each test verifies, which directly feeds into acceptance criteria for the corresponding feature beans.
- The traceability report should cross-reference test patterns with the components/APIs/routes they test.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Add TestPatternSurface to surfaces.py and extend SurfaceCollection | Developer | — | — | — | — |
| 2 | Implement test_patterns.py analyzer | Developer | — | — | — | — |
| 3 | Add bean template renderer for test patterns | Developer | — | — | — | — |
| 4 | Wire analyzer into pipeline Stage C | Developer | — | — | — | — |
| 5 | Add coverage gate and gap query | Developer | — | — | — | — |
| 6 | Write unit tests | Tech-QA | — | — | — | — |
| 7 | Run lint, type-check, and test suite | Tech-QA | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 7 |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |