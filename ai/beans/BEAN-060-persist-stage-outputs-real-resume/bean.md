# BEAN-060: Persist Stage Outputs → Real `--resume`

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-060 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

`--resume` only skips Stage A (clone); Stages B–G always re-run because their outputs are never persisted (BEAN-049 made the docs honest about this). Once enrichment becomes agentic and expensive (BEAN-068), re-running C2 because you tweaked a report generator is unacceptable — iterating on prompts against a 100-surface repo must not re-pay the full LLM cost.

## Goal

Each stage's output is serialized to disk under `<out>/state/`; `--resume` rehydrates completed stages and re-runs only incomplete/invalidated ones. A new `--from-stage <X>` flag forces re-run from a given stage.

## Scope

### In Scope
- Serialize `InventoryResult`, `StackProfile`, `SurfaceCollection` (pre- and post-enrichment) to JSON under `<out>/state/` (`SurfaceCollection.to_dict()` already exists; add `from_dict()` rehydration for every surface type)
- `StateManager` gains per-stage output paths + content hashes; a stage is resumable only if its inputs' hashes match
- Replace the mutable-locals stage plumbing in `pipeline.py` with a `StageOutputs` dataclass (also improves mypy-strict ergonomics)
- `--from-stage` CLI flag; `--resume` becomes genuinely incremental
- Remove the dummy-`CloneResult` reconstruction hack on resume

### Out of Scope
- Caching individual LLM responses (BEAN-068's concern)
- Cross-run caching between different repos

## Acceptance Criteria

- [ ] After a full run, deleting `beans/` and re-running with `--resume` regenerates beans without re-running analyzers or enrichment
- [ ] `--from-stage C2` re-runs enrichment and later stages only
- [ ] Round-trip test: every surface type survives `to_dict()` → `from_dict()` equality
- [ ] Integration test covers resume-after-interrupt at stage boundaries
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), plumbing
- Wave 1 — no dependencies. Soft prerequisite for BEAN-068 (iterating on agentic enrichment affordably)
