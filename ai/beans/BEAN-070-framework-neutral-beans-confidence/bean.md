# BEAN-070: Framework-Neutral Bean Language + Confidence/Gaps Fields

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-070 |
| **Status** | Done |
| **Priority** | Medium |
| **Created** | 2026-07-03 |
| **Completed** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Beans describe surfaces in source-framework terms ("uses `express-session` middleware"). For rebuild-in-a-different-stack, requirements must be behavioral ("users authenticate via session cookie with 30-minute idle expiry") with source-framework details clearly quarantined. Separately, beans don't say how much to trust them: extraction confidence and known unknowns are invisible, so a rebuild agent can't tell solid requirements from guesses — it will hallucinate confidently exactly where the harvest was weakest.

## Goal

Every bean separates framework-neutral requirements from a clearly-labeled "Source Implementation Notes" section, and carries structured `confidence` and `gaps` in frontmatter.

## Scope

### In Scope
- Bean frontmatter additions: `confidence: declared|inferred|llm`, `gaps: [...]` (populated from surface-level markers introduced by BEAN-062/068 where present; empty defaults otherwise)
- Template pass over `beans/templates.py`: requirement sections state behavior neutrally; framework/library specifics move to a `## Source Implementation Notes` section
- Enrichment prompts (system prompt) instructed to phrase behavior framework-neutrally
- A "Gaps & Unknowns" section renders when gaps exist (visible, not buried in frontmatter)
- REQUIREMENTS.md rolls up gap counts per section

### Out of Scope
- New extraction (renders what surfaces already carry)
- Retroactive re-render of previously harvested outputs

## Acceptance Criteria

- [x] No requirement statement in fixture-harvest beans names a source framework/library outside "Source Implementation Notes" (spot-check assertions in tests)
- [x] All beans carry `confidence` + `gaps` frontmatter; unknown-contract surfaces show a rendered Gaps section
- [x] REQUIREMENTS.md shows a gaps rollup
- [x] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track B
- Wave 1 — no hard deps (fields default empty until 062/068 populate them); coordinate template edits with any concurrently-landing renderers

## Implementation Notes (Tech-QA)

- `derive_confidence_and_gaps()` in templates.py: ladder declared > inferred > llm > structural; gaps from `{"unknown": true}` contract markers + `enrichment["gaps"]` (BEAN-068 will populate the latter).
- All 16 renderers pass the surface through; frontmatter gains `confidence:` + `gaps:` keys; a "## Gaps & unknowns" section renders when gaps exist.
- REQUIREMENTS.md gains a "Known Gaps" rollup section (count + pointer).
- Framework-neutral language: audit found the templates already neutral by construction (framework names only enter via surface data); added an explicit neutral-phrasing directive to the enrichment SYSTEM_PROMPT.
- 10 unit tests.
