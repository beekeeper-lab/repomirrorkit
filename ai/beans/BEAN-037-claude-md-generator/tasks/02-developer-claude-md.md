# Task 02: Implement claude_md.py Generator

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends On** | 1 |
| **Status** | Done |
| **Started** | 2026-02-21 00:43 |
| **Completed** | 2026-02-21 00:43 |
| **Duration** | < 1m |

## Goal

Implement `src/repo_mirror_kit/harvester/generator/claude_md.py` that generates CLAUDE.md from surfaces, detected stack, and project metadata.

## Definition of Done

- [x] `generate_claude_md()` function produces complete CLAUDE.md content
- [x] Includes project name and tech stack header
- [x] Includes Stack Quick Reference table from detected stacks and surfaces
- [x] Includes cross-cutting safety rules (customized by detected surfaces)
- [x] Includes cross-cutting quality rules
- [x] Includes team roster from generated agents
- [x] Includes workflow reference section