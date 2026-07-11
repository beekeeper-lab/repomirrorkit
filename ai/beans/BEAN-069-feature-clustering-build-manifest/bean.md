# BEAN-069: Feature Clustering Stage (C3) + `build-manifest.json`

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-069 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

100 disjoint per-surface beans are not a spec. A rebuild orchestrator needs vertical slices — "Order management = these 3 screens, 5 endpoints, 2 models, 4 rules" — plus a dependency-ordered build plan. Today no artifact groups surfaces into features or orders the work, so any rebuild agent must invent its own decomposition (unrepeatable, and it destroys cross-run comparability for orchestration experiments).

## Goal

A new pipeline stage (C3, after enrichment) clusters surfaces into features, emits `features/FEAT-*.md` (feature-level specs referencing member beans) and `build-manifest.json` — a machine-readable DAG of features and beans with dependency ordering that a rebuild orchestrator consumes directly.

## Scope

### In Scope
- Deterministic clustering baseline: connected components over existing cross-refs (route↔component↔api↔model, traceability graph) + path/name affinity
- Optional LLM refinement of cluster naming/membership when enrichment is on (deterministic fallback always available — experiments need reproducibility)
- `features/FEAT-###-<slug>.md`: overview, member surfaces/beans, user-facing behavior summary, feature-level acceptance criteria rollup
- `build-manifest.json`: features + beans with `depends_on` edges (models before APIs before screens; auth before protected features), suggested build order (topo sort), and per-bean `confidence`/`gaps` rollups
- Manifest JSON schema documented + validated in tests; wired into Stage ordering (C2 → C3 → D); REQUIREMENTS.md links features
- Integration test asserts fixture harvest produces ≥2 sensible clusters

### Out of Scope
- The rebuild orchestrator itself (lives outside RepoMirrorKit)
- Gherkin generation (BEAN-074 consumes clusters)

## Acceptance Criteria

- [ ] Fixture harvest emits `features/` with every surface assigned to exactly one feature (or an explicit `misc` cluster)
- [ ] `build-manifest.json` validates against its schema and topo-sorts without cycles
- [ ] Clustering with LLM off is deterministic across runs (byte-identical manifest)
- [ ] Feature files link member beans; beans gain a `feature:` frontmatter key
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track B
- Wave 3 — soft dep: BEAN-068 (richer clusters), works on structural cross-refs alone
- The manifest is the interface between RepoMirrorKit and the user's agentic build experiments — design it with Architect + BA input
