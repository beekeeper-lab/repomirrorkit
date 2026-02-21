# Task 04: Implement agents.py Generator

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Depends On** | 1, 3 |
| **Status** | Done |
| **Started** | 2026-02-21 00:43 |
| **Completed** | 2026-02-21 00:43 |
| **Duration** | < 1m |

## Goal

Implement `src/repo_mirror_kit/harvester/generator/agents.py` that generates agent files based on project characteristics.

## Definition of Done

- [x] Always generates developer, architect, tech-qa agents (minimum 3)
- [x] Conditionally generates security-engineer agent (when auth surfaces exist)
- [x] Conditionally generates devops-release agent (when build_deploy surfaces exist)
- [x] Developer agent includes project-specific stack, key files, patterns
- [x] Architect agent includes system overview (component/API/model counts)
- [x] Tech-QA agent includes test framework and distribution info