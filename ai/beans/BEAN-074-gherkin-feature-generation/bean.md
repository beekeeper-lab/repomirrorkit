# BEAN-074: Gherkin `.feature` Generation per Feature Cluster

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-074 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Beans carry Given/When/Then acceptance criteria as Markdown prose, unusable by tooling. Gherkin `.feature` files are the framework-neutral, machine-parseable form — and they become the parity test suite for a rebuilt application: run the same scenarios against original and rebuild, and "functional replacement" stops being a vibe and becomes a pass rate.

## Goal

Stage G emits `<out>/features-gherkin/FEAT-*.feature` — one canonical Gherkin file per BEAN-069 feature cluster, aggregating scenarios from member beans' acceptance criteria and BEAN-065 business rules, syntactically valid and tagged for traceability.

## Scope

### In Scope
- `generator/gherkin.py`: enrichment GWT triples + business rules (validation → rejection scenarios; permissions → authz scenarios; workflow transitions → lifecycle scenarios) → `Feature`/`Scenario` blocks
- Tags: `@BEAN-xxx` per source bean, `@FEAT-xxx`, `@generated`, plus `@gap` on scenarios synthesized from low-confidence data
- Deduplication of near-identical scenarios within a feature
- Syntactic validation via the `gherkin` parser package in tests
- Implementation-neutral step phrasing (no CSS selectors, no framework calls — behavior only), so steps can be bound to any target stack
- REQUIREMENTS.md + feature files cross-link

### Out of Scope
- Step-definition implementations (rebuild/eval concern — BEAN-078 binds steps)
- UI-level E2E script generation

## Acceptance Criteria

- [ ] Fixture harvest emits ≥1 `.feature` per feature cluster; all parse cleanly with the Gherkin parser
- [ ] Every scenario is traceable to a bean via tags
- [ ] Business-rule surfaces produce negative-path scenarios (e.g. invalid input rejected)
- [ ] No scenario references implementation details (reviewed via test heuristics + Tech-QA check)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track C
- Wave 4 — hard dep: BEAN-069 (clusters); quality scales with BEAN-065/068
- Keystone input to BEAN-078's parity scoring
