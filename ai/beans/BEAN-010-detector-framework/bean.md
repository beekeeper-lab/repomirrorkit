# BEAN-010: Detector Framework

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-010 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect which technology stacks are present in a repository (React, Next.js, FastAPI, etc.) to know which analyzers to run. This detection must be pluggable — new stacks can be added without modifying the pipeline. A base framework is needed that defines the detector interface, signal types, and aggregation logic before individual detectors can be implemented.

## Goal

Implement the detector framework: a base `Detector` class, a `Signal` data model, a detector registry, and an aggregation function that runs all registered detectors against the file inventory and produces a combined stack profile.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/base.py`
- `Detector` abstract base class with `detect(inventory) -> list[Signal]` interface
- `Signal` dataclass: stack name, confidence (0.0–1.0), evidence (file paths that triggered detection)
- `StackProfile` dataclass: aggregated signals with detected stacks and their confidence levels
- Detector registry: `register_detector()` and `get_all_detectors()` functions
- `run_detection(inventory) -> StackProfile` aggregation function that runs all registered detectors
- Confidence thresholds: stacks below a minimum confidence (e.g., 0.3) are excluded
- Unit tests for the framework: detector registration, signal aggregation, confidence filtering

### Out of Scope
- Individual stack detectors (BEAN-011 through BEAN-018)
- File inventory scanning (BEAN-009)
- Running analyzers based on detected stacks (BEAN-020+)

## Acceptance Criteria

- [ ] `Detector` ABC defines `detect(inventory) -> list[Signal]` method
- [ ] `Signal` dataclass has: stack_name, confidence (float 0–1), evidence (list of file paths)
- [ ] `StackProfile` holds aggregated detection results with per-stack confidence
- [ ] Detectors can be registered via `register_detector()` and retrieved via `get_all_detectors()`
- [ ] `run_detection()` runs all registered detectors and aggregates signals
- [ ] Stacks below minimum confidence threshold are excluded from the profile
- [ ] Multiple detectors can contribute signals for the same stack (confidences combine)
- [ ] Framework works with zero registered detectors (returns empty profile)
- [ ] Unit tests cover: registration, detection, aggregation, confidence filtering, empty state
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-004 (Harvester Package Setup) and BEAN-009 (File Inventory).
- This bean creates the framework only. Individual detectors (BEAN-011 through BEAN-018) implement the interface.
- Reference: Spec section 2.1 (Target repo types), section 6 Stage B, section 12 ("Make detectors pluggable").
- The spec says: "The architecture is detector-based so additional stacks can be added without rewriting the pipeline."
- Consider using a simple list-based registry rather than metaclass magic. Keep it simple.

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
