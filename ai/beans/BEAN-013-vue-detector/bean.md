# BEAN-013: Vue Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-013 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
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

- [ ] `VueDetector` implements the `Detector` interface
- [ ] Detects Vue via `package.json` dependency
- [ ] Detects Vue via `.vue` file presence
- [ ] Detects Vue via Vite config with Vue plugin
- [ ] Confidence scoring based on evidence strength
- [ ] No false positives on React or Svelte projects
- [ ] Unit tests cover: Vue repo, non-Vue repo
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

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
