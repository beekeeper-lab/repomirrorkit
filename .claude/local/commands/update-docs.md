# /update-docs Command

Claude Code slash command that detects documentation drift and proposes updates.

## Purpose

Find documentation that has fallen out of sync with the codebase. Compares docs against recent code, config, and dependency changes to identify stale sections, then proposes specific updates. Catches the silent decay that makes onboarding painful and runbooks unreliable.

## Usage

```
/update-docs [project-dir] [--since <ref-or-date>] [--fix]
```

- `project-dir` -- Project root. Defaults to current working directory.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Project directory | Positional argument or cwd | Yes |
| Change scope | `--since` flag | No (defaults to all changes) |
| Specific docs | `--docs` flag | No (defaults to all markdown files) |

## Process

1. **Discover docs** -- Find all markdown files in the project.
2. **Detect changes** -- Identify code, config, and dependency changes since the last doc update.
3. **Map and compare** -- Check each doc section against current reality.
4. **Report** -- Produce a drift report with proposed updates.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Drift report | stdout (or `--output` path) | Stale docs, missing docs, and proposed updates |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--since <ref>` | None | Scope changes to a git ref or date (e.g., `v1.0.0`, `2025-01-01`) |
| `--docs <paths>` | All markdown files | Comma-separated list of specific doc files to check |
| `--output <path>` | stdout | Write the drift report to a file |
| `--fix` | `false` | Apply proposed updates directly instead of just reporting |
| `--check-completeness` | `true` | Verify standard docs exist (README, architecture, ADR index) |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ProjectDirNotFound` | Directory does not exist | Check the path |
| `NoDocsFound` | No markdown files in the project | Create at minimum a README.md |
| `SinceRefInvalid` | Git ref or date not recognized | Use a valid tag, branch, hash, or ISO date |

## Examples

**Check all docs in the current project:**
```
/update-docs
```
Scans all markdown files and reports any that are stale relative to the codebase.

**Check changes since a release:**
```
/update-docs --since v1.2.0
```
Only flags documentation that drifted due to changes made after v1.2.0.

**Auto-fix drift:**
```
/update-docs --fix
```
Applies proposed updates directly to the documentation files. Review changes in git diff afterward.

**Check specific docs:**
```
/update-docs --docs README.md,docs/architecture.md
```
Only checks the specified files for drift.
