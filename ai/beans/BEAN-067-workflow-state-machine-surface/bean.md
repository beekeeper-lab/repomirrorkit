# BEAN-067: `WorkflowSurface` — Entity State Machines

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-067 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Entity lifecycles (order: draft → submitted → paid → shipped; user: invited → active → suspended) encode core business behavior, but no surface captures states or legal transitions. A rebuild that allows shipping an unpaid order fails functional parity in the way users notice most.

## Goal

A `WorkflowSurface` capturing, per stateful entity: the state set, transitions (from → to, trigger, guard), and the surfaces that perform each transition.

## Scope

### In Scope
- `WorkflowSurface` dataclass: `entity_ref`, `states: list[str]`, `transitions: list[Transition]` (`from_state`, `to_state`, `trigger_ref`, `guard`), `confidence`
- Heuristic detection: status/state enum fields on models (leverages BEAN-066 enum extraction) + assignments to those fields traced to the containing function/endpoint
- Library-declared machines (highest confidence): `transitions`/`django-fsm` (Python), XState (JS/TS) — declared states/events extracted directly
- Cross-ref: each transition's `trigger_ref` points at the API/route surface that performs it
- Bean renderer; fixture extended with a small status workflow

### Out of Scope
- Full dataflow analysis to prove transition completeness (agentic enrichment refines; heuristics + declared machines are v1)
- Diagram generation (BEAN-075 renders these surfaces)

## Acceptance Criteria

- [ ] Fixture entity with a status enum + two transition endpoints yields a `WorkflowSurface` with correct states and ≥2 transitions
- [ ] An XState or `transitions` declaration extracts the full declared machine with `declared` confidence
- [ ] Transitions reference the triggering API/route surface where resolvable
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A
- Wave 1–2 — soft dep: BEAN-061 (JS/TS tracing), BEAN-066 (enum reuse). Python-only start is viable immediately
- Feeds BEAN-075 (state diagrams) and BEAN-074 (transition scenarios)
