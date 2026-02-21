# BEAN-034: Dependency & Package Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-034 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-20 |
| **Started** | 2026-02-21 00:10 |
| **Completed** | 2026-02-21 00:21 |
| **Duration** | 11m |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester analyzes application code (routes, components, APIs, models) but does not extract the dependency tree. A developer recreating the app needs to know which libraries are used, their versions, and their purpose. Without dependency analysis, generated requirements are incomplete — they describe behavior but not the toolchain needed to implement it.

## Goal

Implement a dependency and package analyzer that extracts declared dependencies from manifest files (package.json, requirements.txt, pyproject.toml, go.mod, *.csproj, Gemfile, Cargo.toml), classifies them by purpose (runtime, dev, test, build), and produces `DependencySurface` objects for bean generation.

## Scope

### In Scope
- New surface dataclass: `DependencySurface` with fields for package name, version constraint, purpose category, manifest file, and whether it's a direct or transitive dependency
- Add `dependencies` list to `SurfaceCollection`
- Implement `src/repo_mirror_kit/harvester/analyzers/dependencies.py`
- Detect dependencies from:
  - **JavaScript/TypeScript**: package.json (dependencies, devDependencies, peerDependencies)
  - **Python**: pyproject.toml, requirements*.txt, setup.cfg, Pipfile
  - **Go**: go.mod
  - **.NET**: *.csproj PackageReference entries
  - **Ruby**: Gemfile
  - **Rust**: Cargo.toml
- Classify dependencies by purpose: runtime, dev, test, build, peer
- Detect lock files and note their presence (package-lock.json, uv.lock, poetry.lock, yarn.lock, go.sum, Cargo.lock)
- Bean template renderer for dependency beans
- Wire into pipeline Stage C
- Coverage gate and gap query for dependencies
- Unit tests

### Out of Scope
- Transitive dependency resolution (only direct declarations)
- Vulnerability scanning or security audit
- License compatibility analysis
- Version upgrade recommendations
- Downloading or installing packages

## Acceptance Criteria

- [x] `DependencySurface` dataclass exists with name, version, purpose, manifest_file, is_direct fields
- [x] `SurfaceCollection.dependencies` list field exists
- [x] Detects JS/TS dependencies from package.json (all dependency groups)
- [x] Detects Python dependencies from pyproject.toml and requirements*.txt
- [x] Detects Go dependencies from go.mod
- [x] Detects .NET dependencies from *.csproj
- [x] Detects Ruby dependencies from Gemfile
- [x] Detects Rust dependencies from Cargo.toml
- [x] Classifies each dependency as runtime, dev, test, build, or peer
- [x] Records presence of lock files in surface metadata
- [x] Bean template renders dependency beans with version, purpose, and manifest source
- [x] Coverage gate checks dependency coverage (threshold >= 80%)
- [x] Gap query identifies dependencies without beans
- [x] Unit tests cover each ecosystem's manifest parsing
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Add DependencySurface to surfaces.py and extend SurfaceCollection | Developer | — | Done |
| 2 | Implement dependencies.py analyzer | Developer | 1 | Done |
| 3 | Add bean template renderer for dependencies | Developer | 1 | Done |
| 4 | Wire analyzer into pipeline Stage C | Developer | 2 | Done |
| 5 | Add coverage gate and gap query | Developer | 1 | Done |
| 6 | Write unit tests | Tech-QA | 2, 3 | Done |
| 7 | Run lint, type-check, and test suite | Tech-QA | 4, 5, 6 | Done |

## Notes

- Depends on BEAN-009 (file inventory), BEAN-010 (detector framework), BEAN-019 (surface data model).
- Follows established analyzer pattern: `analyze_dependencies(inventory, profile, workdir) -> list[DependencySurface]`.
- Lock file detection is metadata-only (presence/absence); parsing lock files for transitive deps is out of scope.
- LLM enrichment (Stage C2) can add behavioral descriptions explaining what each major dependency provides.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Add DependencySurface to surfaces.py and extend SurfaceCollection | Developer | — | — | — | — |
| 2 | Implement dependencies.py analyzer | Developer | — | — | — | — |
| 3 | Add bean template renderer for dependencies | Developer | — | — | — | — |
| 4 | Wire analyzer into pipeline Stage C | Developer | — | — | — | — |
| 5 | Add coverage gate and gap query | Developer | — | — | — | — |
| 6 | Write unit tests | Tech-QA | — | — | — | — |
| 7 | Run lint, type-check, and test suite | Tech-QA | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 7 |
| **Total Duration** | 11m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |