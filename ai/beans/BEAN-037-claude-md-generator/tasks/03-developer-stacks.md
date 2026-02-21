# Task 03: Implement stacks.py Generator

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends On** | 1 |
| **Status** | Done |
| **Started** | 2026-02-21 00:43 |
| **Completed** | 2026-02-21 00:43 |
| **Duration** | < 1m |

## Goal

Implement `src/repo_mirror_kit/harvester/generator/stacks.py` that generates stack convention files from detected frameworks and patterns.

## Definition of Done

- [x] `generate_stacks()` produces language-specific convention files
- [x] Supports Python, JavaScript/TypeScript, .NET, Go, Ruby
- [x] Falls back to generic conventions when no specific language matched
- [x] Each stack file includes language, framework, test, linter, and project structure sections