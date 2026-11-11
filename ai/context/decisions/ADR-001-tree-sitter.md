# ADR-001: tree-sitter for JS/TS/C# structural extraction

**Status:** Accepted (2026-11-11, BEAN-061)

## Context
Regex extraction cannot recover request/response contracts, form fields, validation rules, or state machines from JS/TS/C#. Python already uses stdlib `ast`.

## Decision
Add `tree-sitter` plus the `tree-sitter-javascript`, `tree-sitter-typescript` and `tree-sitter-c-sharp` grammar wheels (all MIT, maintained, prebuilt wheels, no compiler needed). Access goes through `harvester/parsing/treesitter.py`.

## Consequences
- Analyzers must treat a missing grammar or a parse failure as "fall back to the regex result", never a crash (`parse_source` returns `None`).
- Dependency discipline: four new runtime deps, all pure-wheel; reviewed for license (MIT) and security posture (parse-only, no code execution, input size already capped by BEAN-047 and inventory limits).
- Further grammars (Java, Go, Vue SFC script blocks) are added the same way.
