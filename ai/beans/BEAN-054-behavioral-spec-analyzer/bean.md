# BEAN-054: Behavioral-Spec Analyzer (Docstrings + Test Names)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-054 |
| **Status** | In Progress |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 16:49 |
| **Completed** | — |
| **Duration** | — |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

The harvester's analyzers extract **structure** — routes, components, models, APIs — but they do not extract **intent**. As a result, even a fully-populated bean today reads like "Route GET /users at file foo.py:23" rather than "Users page lists active team members and shows their role." Without LLM enrichment, behavior is captured nowhere; with LLM enrichment, behavior is inferred from raw source code by Claude, which is expensive and ignores high-quality intent signal that already exists in the codebase: docstrings, function/test names, JSDoc comments, and pytest test names like `test_user_can_log_in_with_valid_credentials`. These are explicit human-authored statements of what the code is supposed to do — and the harvester is currently throwing them away.

## Goal

A new analyzer extracts intent signal from docstrings, test names, JSDoc/TSDoc comments, and other human-authored "what this does" markers in the source. Each extracted intent is attached to the relevant surface as enrichment data. Beans rendered without LLM enrichment now contain real behavioral content, and beans rendered *with* LLM enrichment use this signal as high-quality input to Claude (less hallucination, less cost).

## Scope

### In Scope
- New analyzer `src/repo_mirror_kit/harvester/analyzers/behavioral_spec.py` with a `analyze_behavioral_spec(inventory: InventoryResult, profile: StackProfile, workdir: Path, surfaces: SurfaceCollection) -> None` function
- Extraction sources, prioritized by signal-to-noise:
  - Python: function/class docstrings (`ast` module)
  - JS/TS: leading JSDoc/TSDoc comments
  - Test names: pytest `test_*` function names, Jest/Vitest `it(...)` strings, `describe(...)` strings
  - Top-of-file module docstrings as a context layer
- Map each extracted intent to the relevant surface by file path + line proximity (the analyzer is a *post-pass* that runs after the surface analyzers; it does not produce its own surface type)
- Attach to each surface's `enrichment` dict under a new `behavioral_signals` key with structure: `{"docstring": str | None, "test_names": list[str], "jsdoc": str | None}`
- Update bean templates (`harvester/beans/templates.py`) so the "Behavioral description" section uses `behavioral_signals` when LLM enrichment is absent (replacing the literal "TODO" placeholder at `templates.py:117`)
- Wire the analyzer into Stage C in `pipeline.py` after the existing analyzers, before `surfaces` is finalized
- Unit tests covering extraction from each language and source type
- Integration test (BEAN-050) updated to assert behavioral_signals are populated for the fixture's documented routes

### Out of Scope
- Inferring behavior from code shape (data flow, control flow) — that's the LLM's job in Stage C2
- NLP normalization of docstring text — pass through verbatim
- Cross-language intent — keep the extractor language-aware
- Markdown extraction from README sections — separate concern

## Acceptance Criteria

- [ ] New analyzer module exists with the documented signature
- [ ] Surfaces with associated docstrings have `behavioral_signals.docstring` populated after Stage C
- [ ] Surfaces with associated tests have `behavioral_signals.test_names` populated with at least the test name strings
- [ ] Bean rendering without LLM enrichment shows real behavioral content for surfaces that have signals (no more literal "TODO: Describe the expected behavior")
- [ ] Bean rendering with LLM enrichment continues to use the LLM's `behavioral_description` (LLM signal takes precedence; behavioral_signals are still passed in as input)
- [ ] Unit tests cover Python AST extraction, JSDoc extraction, pytest test-name extraction, Jest test-name extraction
- [ ] Integration test asserts a known fixture surface has the expected docstring captured
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 3 (2026-05-01)
- Depends on BEAN-050 (integration test) as safety net
- This bean is what makes the harvester useful **without** an API key. After this lands, beans contain real behavioral content even in offline / no-LLM mode.
- Architect should decide whether this is an "analyzer" or a "post-pass enricher" — the design is similar to LLM enrichment (Stage C2) and may belong in `harvester/llm/` or a new `harvester/enrichment/` subdir rather than `harvester/analyzers/`. Recommendation: keep in `analyzers/` since it produces signal directly from source rather than a model

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
