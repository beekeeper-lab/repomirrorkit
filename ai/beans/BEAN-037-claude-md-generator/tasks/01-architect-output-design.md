# Task 01: Design Output Directory Structure and CLAUDE.md Template

| Field | Value |
|-------|-------|
| **Owner** | Architect |
| **Depends On** | — |
| **Status** | Done |
| **Started** | 2026-02-21 00:33 |
| **Completed** | 2026-02-21 00:33 |
| **Duration** | < 1m |

## Goal

Define the output directory layout for the generated Claude Code project folder and the CLAUDE.md template structure.

## Design

### Output Directory Structure

```
output/project-folder/
├── CLAUDE.md                           # Main project instructions
├── .claude/
│   └── agents/
│       ├── developer.md                # Always generated
│       ├── architect.md                # Always generated
│       ├── tech-qa.md                  # Always generated
│       ├── security-engineer.md        # Conditional: auth surfaces exist
│       └── devops-release.md           # Conditional: build_deploy surfaces exist
└── ai/
    └── stacks/
        └── <language>.md               # One per detected primary language/framework
```

### CLAUDE.md Template Sections

1. **Header** — Project name and description (derived from README or repo name)
2. **Tech Stack** — Table of detected frameworks, languages, and tools
3. **Stack Quick Reference** — Concern/tool table per primary language (mirrors this project's CLAUDE.md format)
4. **Cross-Cutting Safety Rules** — Standard 8-rule set, customized based on detected patterns
5. **Cross-Cutting Quality Rules** — Standard 8-rule set
6. **Team Roster** — Table of active personas with agent file references
7. **Workflow Reference** — Table pointing to generated beans, surface map, traceability, coverage

### Key Design Decisions

- CLAUDE.md mirrors this project's own structure (proven template)
- Safety rules include conditionals (e.g., SQL injection rule only if data layer detected)
- Team roster only includes agents that were generated (not all 10)
- Stack quick reference is language-specific (Python, JavaScript/TypeScript, .NET, Go)

## Definition of Done

- [x] Directory structure defined
- [x] CLAUDE.md template sections defined
- [x] Design documented in this task file