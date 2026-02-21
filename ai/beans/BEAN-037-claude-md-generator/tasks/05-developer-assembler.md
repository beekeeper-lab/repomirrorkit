# Task 05: Implement assembler.py Orchestrator

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends On** | 2, 3, 4 |
| **Status** | Done |
| **Started** | 2026-02-21 00:43 |
| **Completed** | 2026-02-21 00:43 |
| **Duration** | < 1m |

## Goal

Implement `src/repo_mirror_kit/harvester/generator/assembler.py` that orchestrates all generators and creates the output directory structure.

## Definition of Done

- [x] `assemble_project_folder()` orchestrates stacks → agents → CLAUDE.md generation
- [x] Creates output directory structure: project-folder/.claude/agents/, project-folder/ai/stacks/, project-folder/CLAUDE.md
- [x] Returns `GeneratorResult` with generated file count, agent count, stack count
- [x] Creates parent directories as needed