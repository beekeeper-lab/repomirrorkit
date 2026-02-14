# /release-notes Command

Claude Code slash command that generates release notes and a changelog entry from completed work.

## Purpose

Produce structured release notes by collecting completed tasks, merged changes, and known issues from a release cycle. Outputs both user-facing release notes and a changelog entry in Keep a Changelog format. Ensures every change is documented and breaking changes are prominently flagged.

## Usage

```
/release-notes <version> [--previous <version>] [--audience <internal|external|both>]
```

- `version` -- Version identifier for this release (required).

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Version | Positional argument | Yes |
| Previous version | `--previous` flag | No |
| Tasks directory | `--tasks` flag or `ai/tasks/` | No |
| Changelog | `--changelog` flag or `CHANGELOG.md` | No |

## Process

1. **Collect completed work** -- Gather completed tasks and group by category.
2. **Gather change summaries** -- Pull PR descriptions and merge commits if git is available.
3. **Flag breaking changes** -- Identify API, config, or behavior changes requiring consumer action.
4. **Compile known issues** -- List open items and limitations.
5. **Draft notes and changelog** -- Produce structured output tailored to the audience.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Release notes | `ai/outputs/devops-release/release-{version}.md` | Full release notes |
| Changelog update | `CHANGELOG.md` (appended) | New entry in Keep a Changelog format |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--previous <version>` | Auto-detected | Previous version for scoping changes |
| `--audience <level>` | `both` | `internal`: technical details. `external`: user-facing only. `both`: both variants |
| `--tasks <dir>` | `ai/tasks/` | Directory of task files |
| `--changelog <path>` | `CHANGELOG.md` | Path to the changelog file |
| `--output <dir>` | `ai/outputs/devops-release/` | Override the output directory |
| `--dry-run` | `false` | Preview notes without writing files or appending changelog |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoVersionProvided` | No version supplied | Provide a version string as the first argument |
| `NoCompletedTasks` | No completed tasks found | Verify task status or check the tasks directory |
| `ChangelogNotFound` | Changelog file does not exist | Create `CHANGELOG.md` or specify the correct path |

## Examples

**Generate release notes:**
```
/release-notes 1.2.0
```
Collects all completed work, produces release notes and appends to CHANGELOG.md.

**Scoped to a version range:**
```
/release-notes 1.2.0 --previous 1.1.0
```
Only includes changes between v1.1.0 and v1.2.0.

**External audience only:**
```
/release-notes 2.0.0 --audience external
```
Produces user-facing release notes, omitting internal refactoring and infrastructure changes.

**Preview without writing:**
```
/release-notes 1.3.0 --dry-run
```
Displays the notes in the terminal without modifying any files.
