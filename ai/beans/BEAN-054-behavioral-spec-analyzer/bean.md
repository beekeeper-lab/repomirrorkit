# BEAN-054: Behavioral-Spec Analyzer (Docstrings + Test Names)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-054 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 16:49 |
| **Completed** | 2026-05-01 16:54 |
| **Duration** | 6h 3m |
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
| 1 | Behavioral-spec analyzer + bean template integration | developer | — | Done |
| 2 | Verify extraction + bean rendering fallback | tech-qa | 01 | Done |

> Skipped: BA, Architect (analyzer pattern follows existing patterns; design recorded inline).

### Verification (Tech-QA)

- ✅ New module `src/repo_mirror_kit/harvester/analyzers/behavioral_spec.py` with `analyze_behavioral_spec(inventory, profile, workdir, surfaces)` running as a Stage C post-pass after the surface analyzers.
- ✅ Three signal sources extracted, attached to `surface.enrichment["behavioral_signals"]`:
  - **Python docstrings**: AST walks the source file once per file (cached) and finds the smallest enclosing `FunctionDef` / `AsyncFunctionDef` / `ClassDef` containing the surface's `start_line`. Falls back to module docstring.
  - **JSDoc/TSDoc comments**: scans backwards from the surface's source line for the nearest `/** ... */` block, strips `*` markers, returns cleaned body. Handles blank lines between block and target.
  - **Test names** (pytest test functions + Jest/Vitest/Mocha `it/test/describe/context` strings): collected once per harvest from inventory test files. Matched to surfaces by camelCase-aware token overlap (`UserLogin` → `{user, login}` matches `test_user_can_log_in`). Capped at 10 per surface.
- ✅ Bean templates (`harvester/beans/templates.py`) updated: when LLM `behavioral_description` is absent but `behavioral_signals` is present, render docstring blockquote + JSDoc blockquote + test-name list under the **Behavioral description** heading. The literal `"TODO: Describe..."` placeholder only appears when there is **no** signal at all. **This is the headline goal-alignment payoff: beans without an API key now contain real behavioral content.**
- ✅ Idempotent: a pre-existing `behavioral_signals` entry is preserved, not clobbered.
- ✅ Failure-mode hardening: parse errors, missing files, malformed JSDoc all silently skipped (this is enrichment, not core analysis).
- ✅ 23 unit tests in `tests/unit/test_behavioral_spec.py`: Python docstring extraction (function, class, module fallback, none), JSDoc extraction (single-line, multi-line, blank-line handling, no-jsdoc, body cleaning), test-name extraction (sync, async, syntax-error tolerance, non-test skip), name matching (substring, camelCase tokens, short-name skip, 10-cap), top-level integration (Python docstring on route, JSDoc on api, test-name attachment, no-clobber, no-signal, broken-source tolerance).
- ✅ Suite: 1772 passed (up from 1749; +23 new). Ruff clean.

Note: the bean's "module docstring as a context layer" sub-item is implemented as a fallback inside `_python_docstring_at` rather than as a separate signal — simpler and matches the spec.

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 3 (2026-05-01)
- Depends on BEAN-050 (integration test) as safety net
- This bean is what makes the harvester useful **without** an API key. After this lands, beans contain real behavioral content even in offline / no-LLM mode.
- Architect should decide whether this is an "analyzer" or a "post-pass enricher" — the design is similar to LLM enrichment (Stage C2) and may belong in `harvester/llm/` or a new `harvester/enrichment/` subdir rather than `harvester/analyzers/`. Recommendation: keep in `analyzers/` since it produces signal directly from source rather than a model

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Behavioral-spec analyzer + bean template integration | developer | — | — | — | — |
| 2 | Verify extraction + bean rendering fallback | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 2 |
| **Total Duration** | 6h 3m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |