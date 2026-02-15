# BEAN-011: React Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-011 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect whether a repository uses React so it can activate the appropriate route, component, and UI analyzers. React detection requires checking for React dependencies, JSX/TSX files, and common React patterns (hooks, component exports).

## Goal

Implement a React detector that identifies React projects by examining `package.json` dependencies, file extensions (`.jsx`, `.tsx`), and common React patterns, producing a confidence-scored signal.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/react.py`
- Detect React via:
  - `react` in `package.json` dependencies or devDependencies
  - Presence of `.jsx` or `.tsx` files
  - Import patterns: `import React`, `from 'react'`, `import { useState }` etc.
  - Common file patterns: `App.jsx`, `App.tsx`, `index.jsx`
- Confidence scoring: high confidence if package.json + JSX files, medium if only one signal
- Register with the detector framework (BEAN-010)
- Unit tests with sample inventory data

### Out of Scope
- Next.js-specific detection (BEAN-012 — separate detector with higher specificity)
- React Native detection
- Deep component analysis (BEAN-021)
- Route extraction from React Router (BEAN-020)

## Acceptance Criteria

- [ ] `ReactDetector` implements the `Detector` interface from BEAN-010
- [ ] Detects React via `package.json` dependency check
- [ ] Detects React via `.jsx`/`.tsx` file presence
- [ ] Detects React via import pattern matching
- [ ] Confidence score reflects strength of evidence (multiple signals = higher confidence)
- [ ] Evidence list includes the specific files/paths that triggered detection
- [ ] Registered in the detector registry
- [ ] Returns empty signals for non-React repos (no false positives)
- [ ] Unit tests cover: React repo detection, non-React repo, partial signals
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-010 (Detector Framework).
- The React detector should not claim Next.js-specific patterns — the Next.js detector (BEAN-012) handles those with higher specificity.
- Reference: Spec section 2.1 (Target repo types), section 6 Stage B.

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
