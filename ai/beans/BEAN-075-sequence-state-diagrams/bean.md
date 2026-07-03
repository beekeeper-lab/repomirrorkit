# BEAN-075: Sequence + State Mermaid Diagrams

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-075 |
| **Status** | Unapproved |
| **Priority** | Low |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Humans reviewing a harvest (and approving a rebuild plan) need to *see* key operations and entity lifecycles. The structured data will exist (BEAN-067 workflows, BEAN-068 traced flows); without renderings, reviewers must reconstruct flows from bean prose.

## Goal

Stage G emits `<out>/diagrams/`: a Mermaid `sequenceDiagram` per traced key operation (from BEAN-068 `traced_flow` hops) and a Mermaid `stateDiagram-v2` per `WorkflowSurface`. Diagrams are renderings of surface data, never hand-authored.

## Scope

### In Scope
- `generator/diagrams.py`: `traced_flow` hop lists → sequence diagrams (participants = screen/API/service/model refs); `WorkflowSurface` → state diagrams (states + labeled transitions)
- Selection heuristic: sequence diagrams only for feature-cluster primary flows (avoid 200 trivial diagrams); cap + note what was skipped
- Mermaid syntax validation tests (same approach as BEAN-055)
- Feature files (BEAN-069) and REQUIREMENTS.md embed/link relevant diagrams

### Out of Scope
- Class/component diagrams (low recreation value)
- Diagram editing round-trips

## Acceptance Criteria

- [ ] Fixture with a workflow yields a compiling `stateDiagram-v2` matching the surface's states/transitions
- [ ] A traced flow yields a compiling `sequenceDiagram` with hops in order
- [ ] Skipped-diagram count is logged/reported (no silent truncation)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track C
- Wave 3 — hard dep: BEAN-067 (state); BEAN-068's `traced_flow` (sequence). State-only subset can land with just 067
