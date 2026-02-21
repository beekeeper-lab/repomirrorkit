# BEAN-038: File Coverage Analysis & Uncovered File Detection

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-038 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-21 |
| **Started** | 2026-02-21 00:24 |
| **Completed** | 2026-02-21 00:35 |
| **Duration** | 11m |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester's coverage model has a fundamental blind spot. Coverage gates verify that every found surface has a bean, but nothing verifies that every source file is covered by at least one surface. Analyzers are pattern-based (bottom-up) — they only find what they're designed to look for. Business logic modules, utility libraries, service layers, domain-specific code, and anything novel can pass through the entire pipeline without generating a single surface or requirement. Without file-level coverage assurance, there is no guarantee that the harvest captures enough requirements to reproduce the system.

## Goal

Implement a file coverage analysis stage that cross-references the file inventory (Stage B) against all surface `source_refs` to identify uncovered files, generates catch-all surfaces for uncovered files (optionally enriched by LLM), and produces a file coverage report showing per-file coverage status. This closes the loop between "files that exist" and "files we have requirements for."

## Scope

### In Scope
- New surface dataclass: `GeneralLogicSurface` for code that doesn't fit any specialized analyzer — fields for file_path, module_purpose, exports/public_api, complexity_hint
- Add `general_logic` list to `SurfaceCollection`
- Implement `src/repo_mirror_kit/harvester/analyzers/file_coverage.py`:
  - `find_uncovered_files(inventory, surfaces) -> list[Path]` — compares inventory file list against all surface `source_refs`, returns files with zero surface references
  - `analyze_uncovered_files(uncovered_files, inventory, profile, workdir) -> list[GeneralLogicSurface]` — generates catch-all surfaces for uncovered files by extracting module-level information (exports, classes, functions, docstrings)
- File coverage report: `src/repo_mirror_kit/harvester/reports/file_coverage.py`
  - Per-file coverage status: covered (has surface refs), uncovered (no surface refs), excluded (non-source file)
  - Overall file coverage percentage
  - Uncovered file list grouped by directory
  - Coverage heatmap by directory (which directories have lowest coverage)
- Configurable exclusion patterns for files that don't need coverage (migrations, generated code, vendor, __pycache__, .git, node_modules, lock files, etc.)
- Wire `find_uncovered_files` into pipeline after Stage C (all analyzers have run)
- Generate `GeneralLogicSurface` for each uncovered source file
- Bean template renderer for general logic beans
- Coverage gate for file coverage (threshold configurable, default >= 90%)
- LLM enrichment support: when LLM is enabled, Stage C2 reads uncovered files and generates behavioral descriptions of what each module does
- Unit tests

### Out of Scope
- Line-level or function-level coverage (this is file-level only)
- Automatic splitting of large files into multiple surfaces
- Scoring or ranking files by importance
- Suggesting which existing analyzer should have caught a file
- Code quality assessment of uncovered files

## Acceptance Criteria

- [x] `GeneralLogicSurface` dataclass exists with file_path, module_purpose, exports, complexity_hint fields
- [x] `SurfaceCollection.general_logic` list field exists
- [x] `find_uncovered_files()` correctly identifies files with zero surface references
- [x] `find_uncovered_files()` excludes non-source files (images, lock files, generated code, etc.)
- [x] Configurable exclusion patterns (default excludes: migrations/, vendor/, node_modules/, __pycache__/, *.lock, *.min.js, etc.)
- [x] `analyze_uncovered_files()` produces `GeneralLogicSurface` for each uncovered file
- [x] `analyze_uncovered_files()` extracts module-level info: top-level classes, functions, docstring
- [x] File coverage report shows per-file status (covered/uncovered/excluded)
- [x] File coverage report shows overall coverage percentage
- [x] File coverage report groups uncovered files by directory
- [x] Coverage gate fails when file coverage is below threshold
- [x] Bean template renders general logic beans with module purpose, exports, and file path
- [x] LLM enrichment generates behavioral descriptions for uncovered files when enabled
- [x] Pipeline produces file-coverage.md and file-coverage.json in output directory
- [x] Unit tests cover uncovered file detection, exclusion patterns, report generation
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Add GeneralLogicSurface to surfaces.py and extend SurfaceCollection | Developer | — | Done |
| 2 | Implement file_coverage.py analyzer (find_uncovered + analyze_uncovered) | Developer | 1 | Done |
| 3 | Implement file_coverage.py report (per-file status, percentage, directory grouping) | Developer | 2 | Done |
| 4 | Add bean template renderer for general logic | Developer | 1 | Done |
| 5 | Add LLM prompt template for uncovered file enrichment | Developer | 1 | Done |
| 6 | Wire into pipeline: run after Stage C, feed into C2/D/E/F | Developer | 2, 3 | Done |
| 7 | Add coverage gate for file coverage | Developer | 3 | Done |
| 8 | Write unit tests | Tech-QA | 2, 3, 4 | Done |
| 9 | Run lint, type-check, and test suite | Tech-QA | 6, 7, 8 | Done |

## Notes

- Depends on BEAN-009 (file inventory provides the file list), BEAN-019 (surface data model provides source_refs).
- This is the completeness guarantee — it closes the gap between "files that exist" and "files we have requirements for."
- The file inventory (Stage B) already catalogs every file with metadata. Surface `source_refs` already link surfaces back to files. This bean connects those two existing data sources.
- Default exclusion patterns should be generous. Files like `__init__.py`, migration scripts, and generated code rarely need behavioral requirements.
- The `GeneralLogicSurface` is intentionally simple — it's a catch-all. The real value comes from LLM enrichment reading the file and explaining what it does.
- File coverage percentage is a top-level quality metric: "We have requirements covering 94% of source files" is a strong statement about harvest completeness.
- Consider adding the file coverage percentage to the existing coverage report summary alongside surface-level coverage.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Add GeneralLogicSurface to surfaces.py and extend SurfaceCollection | Developer | — | — | — | — |
| 2 | Implement file_coverage.py analyzer (find_uncovered + analyze_uncovered) | Developer | — | — | — | — |
| 3 | Implement file_coverage.py report (per-file status, percentage, directory grouping) | Developer | — | — | — | — |
| 4 | Add bean template renderer for general logic | Developer | — | — | — | — |
| 5 | Add LLM prompt template for uncovered file enrichment | Developer | — | — | — | — |
| 6 | Wire into pipeline: run after Stage C, feed into C2/D/E/F | Developer | — | — | — | — |
| 7 | Add coverage gate for file coverage | Developer | — | — | — | — |
| 8 | Write unit tests | Tech-QA | — | — | — | — |
| 9 | Run lint, type-check, and test suite | Tech-QA | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 9 |
| **Total Duration** | 11m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |