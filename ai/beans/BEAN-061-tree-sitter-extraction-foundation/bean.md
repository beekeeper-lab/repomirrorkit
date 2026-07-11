# BEAN-061: Tree-sitter Extraction Foundation

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-061 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

All analyzers are regex-based (an explicit v1 choice). Regex suffices for names and paths but cannot extract what recreation requires: request/response shapes, form fields with types and validation, business rules, multi-line decorators, dynamically registered routes. Python has stdlib `ast`, but JS/TS/C# — the majority of target repos — have nothing. This is the fidelity ceiling for the whole Track A.

## Goal

A shared parsing service (`harvester/parsing/`) wrapping tree-sitter with language grammars for JavaScript, TypeScript/TSX, and C#, exposing typed query helpers that per-framework analyzers consume. Regex remains as fallback when a grammar is unavailable or parsing fails.

## Scope

### In Scope
- Add `tree-sitter` + language grammar packages as dependencies (dependency-discipline review: maintenance status, licenses — MIT across the board)
- `harvester/parsing/service.py`: parse-with-cache per file, graceful degradation to `None` on parse failure (analyzer then falls back to regex)
- Query helpers: find call expressions by callee name, object-literal → dict extraction, JSX element/attribute walking, decorator extraction, class/property enumeration
- Migrate ONE existing analyzer path as proof (suggest: Express route extraction in `apis.py`) without changing its output schema
- Benchmark guard: parsing the `ts-next` fixture stays within an agreed time budget

### Out of Scope
- Migrating all analyzers (follow-up beans consume the foundation: 063, 064, 065)
- Python parsing (stdlib `ast` already available; BEAN-062 uses it)
- Type inference / symbol resolution (tree-sitter is syntax only — acceptable)

## Acceptance Criteria

- [ ] `parsing` package parses JS, TS, TSX, C# fixture snippets and exposes documented query helpers
- [ ] Express route extraction runs tree-sitter-first, regex-fallback, with identical-or-better results on existing unit tests
- [ ] Parse failure on malformed input degrades to regex path with a structured log, never a crash
- [ ] New dependency documented (ADR per dependency-discipline rule)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A foundation
- Wave 1 — no dependencies. Hard prerequisite for BEAN-063, BEAN-064; partial for BEAN-065
- Architect input wanted on grammar packaging (wheels vs build-from-source) for portability
