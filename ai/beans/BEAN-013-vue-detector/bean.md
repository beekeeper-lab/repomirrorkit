# BEAN-013: Vue Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-013 |
| **Status** | Done |
| **Priority** | Medium |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect Vue.js projects to activate Vue-specific route and component analyzers. Vue has distinct single-file component patterns (`.vue` files), its own router configuration, and specific dependencies.

## Goal

Implement a basic Vue detector that identifies Vue.js projects by examining dependencies, `.vue` files, and Vue-specific configuration.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/vue.py`
- Detect Vue via:
  - `vue` in `package.json` dependencies
  - Presence of `.vue` files (single-file components)
  - `vite.config.*` with Vue plugin references
  - Vue Router configuration files (`router/index.js`, `router/index.ts`)
- Basic detection — not full Vue ecosystem analysis
- Confidence scoring and evidence collection
- Register with detector framework
- Unit tests

### Out of Scope
- Nuxt.js detection (could be a future detector)
- Vue 2 vs Vue 3 differentiation
- Deep Composition API vs Options API analysis

## Acceptance Criteria

- [x] `VueDetector` implements the `Detector` interface
- [x] Detects Vue via `package.json` dependency
- [x] Detects Vue via `.vue` file presence
- [x] Detects Vue via Vite config with Vue plugin
- [x] Confidence scoring based on evidence strength
- [x] No false positives on React or Svelte projects
- [x] Unit tests cover: Vue repo, non-Vue repo
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement VueDetector with 4 signal types in vue.py | Developer | — | Done |
| 2 | Register VueDetector with detector registry | Developer | 1 | Done |
| 3 | Write unit tests (26 tests: interface, signals, false positives, registry) | Tech-QA | 2 | Done |
| 4 | QA verification: ruff, mypy, pytest (382 tests pass, 0 regressions) | Tech-QA | 3 | Done |

## Notes

- Depends on BEAN-010 (Detector Framework).
- Spec marks Vue as "basic" support for v1.
- Reference: Spec section 2.1.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 |      |       |          |           |            |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
