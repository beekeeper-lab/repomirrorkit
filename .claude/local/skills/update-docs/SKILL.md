# Skill: Update Docs

## Description

Detects documentation drift and refreshes project documentation to match the
current state of the codebase. Compares README, runbooks, ADR index, architecture
overview, and onboarding guides against recent changes (code, configuration,
dependencies, API surface) and produces a list of stale sections with proposed
updates. This skill prevents the common failure mode where documentation is
accurate at launch but decays silently as the code evolves.

## Trigger

- Invoked by the `/update-docs` slash command.
- Called by the Technical Writer persona during documentation cycles.
- Useful as a pre-release check to ensure docs ship in sync with code.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| project_dir | Directory path | Yes | Root of the project to check |
| doc_paths | List of file paths | No | Specific docs to check; defaults to auto-discovery of all markdown files |
| since | String | No | Git ref or date to scope change detection (e.g., "v1.0.0", "2025-01-01") |
| composition_spec | File path | No | Composition spec for understanding project structure; auto-detected |

## Process

1. **Discover documentation** -- Find all markdown files in the project: README.md, CLAUDE.md, docs/, ai/context/, runbooks, ADR index. Build an inventory of what documentation exists.
2. **Detect recent changes** -- Using git history (if available) or file modification times, identify what code, configuration, and dependency files changed since the last documentation update or the `since` marker.
3. **Map changes to docs** -- For each changed area, identify which documentation should reflect it:
   - Dependency changes (pyproject.toml, package.json) → README setup instructions, architecture overview
   - API changes (route definitions, schemas) → API docs, architecture overview
   - Configuration changes (.env, config files) → README config section, runbooks
   - New files/directories → project structure docs, onboarding guide
   - ADR additions → ADR index
4. **Check for staleness** -- For each mapping, compare the documentation content against the current state. Flag sections where the documentation contradicts or omits current reality.
5. **Propose updates** -- For each stale section, produce a specific proposed update: what to change, where, and why. Include the current text and the suggested replacement.
6. **Check completeness** -- Verify that standard documentation exists: README (setup, run, test), architecture overview, ADR index, onboarding guide. Flag any that are missing entirely.
7. **Produce drift report** -- Generate a summary listing all stale docs, missing docs, and proposed updates sorted by priority (critical drift first).

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| drift_report | Markdown file | Summary of stale, missing, and outdated documentation with proposed updates |
| proposed_updates | Sections in report | Specific text changes for each stale section |
| completeness_check | Section in report | List of expected standard docs with present/missing status |

## Quality Criteria

- Every changed code area is checked against relevant documentation -- no blind spots.
- Staleness verdicts are specific: "README setup instructions reference pytest 7.x but pyproject.toml pins pytest 8.x" not just "README may be outdated."
- Proposed updates are concrete: include the suggested new text, not just "update this section."
- Missing documentation is flagged with a template or stub to get started.
- The report prioritizes: contradictions (docs say wrong thing) before omissions (docs say nothing) before style issues.
- Running this skill on a freshly-generated project produces zero drift findings.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `ProjectDirNotFound` | Directory does not exist | Check the path |
| `NoDocsFound` | No markdown files found in the project | Create at minimum a README.md |
| `GitHistoryUnavailable` | Not a git repo; change detection limited to file modification times | Results may be less precise without git history |
| `SinceRefInvalid` | The `since` git ref or date is not recognized | Use a valid git tag, branch, commit hash, or ISO date |

## Dependencies

- Git history (optional but recommended) for change detection
- Project markdown files for content analysis
- Composition spec for understanding project structure and team
- No external tooling required beyond git
