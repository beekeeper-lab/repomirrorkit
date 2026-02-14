# Skill: Release Notes

## Description

Collects completed work items, merged changes, and resolved issues from a
release cycle and produces structured release notes, a changelog entry, and
a known issues list. The skill reads task completion records, PR summaries,
and the generation manifest to build a comprehensive picture of what changed,
then formats it for both technical and non-technical audiences. This supports
the DevOps/Release Engineer and Technical Writer personas.

## Trigger

- Invoked by the `/release-notes` slash command.
- Called by the DevOps/Release Engineer persona during release packaging.
- Called by the Technical Writer persona for external-facing communication.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| version | String | Yes | Version identifier for this release (e.g., "1.2.0", "2025-Q1-sprint-3") |
| tasks_dir | Directory path | No | Directory of completed tasks; defaults to `ai/tasks/` |
| previous_version | String | No | Previous version for comparison; used to scope what's "new" |
| changelog_file | File path | No | Existing changelog to append to; defaults to `CHANGELOG.md` |
| audience | Enum: `internal`, `external`, `both` | No | Who the notes are for; defaults to `both` |

## Process

1. **Collect completed work** -- Scan task files for items marked complete since the previous version. Group by category: features, fixes, improvements, documentation, infrastructure.
2. **Gather PR/change summaries** -- If git history is available, collect merge commit messages and PR descriptions for the version range. Cross-reference with task IDs.
3. **Identify breaking changes** -- Flag any changes that alter APIs, data formats, configuration, or behavior in ways that require consumer action.
4. **Compile known issues** -- Collect open tasks, deferred items, and known limitations that ship with this version.
5. **Draft release notes** -- Produce a structured document with sections: highlights (top 3 changes), features, fixes, improvements, breaking changes, known issues, and upgrade instructions.
6. **Draft changelog entry** -- Produce a concise changelog entry following Keep a Changelog format: Added, Changed, Deprecated, Removed, Fixed, Security.
7. **Tailor for audience** -- If `external`, focus on user-facing changes and omit internal refactoring. If `internal`, include technical details and infrastructure changes. If `both`, produce both variants.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| release_notes | Markdown file | Full release notes document for the version |
| changelog_entry | Text (appended) | Entry appended to the existing changelog file |
| known_issues | Section in notes | List of open issues and limitations shipping with this version |

## Quality Criteria

- Every completed task is accounted for in either the release notes or changelog -- nothing is silently dropped.
- Breaking changes are prominently flagged and include migration/upgrade instructions.
- The highlights section contains no more than three items and captures the most impactful changes.
- The changelog entry follows Keep a Changelog conventions (Added/Changed/Fixed/etc.).
- Known issues are honest: they describe the limitation, its impact, and any workaround.
- External-facing notes use user-understandable language; internal notes can use technical shorthand.
- Version identifiers are consistent between the release notes, changelog, and any tagged artifacts.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoVersionProvided` | Version identifier not supplied | Provide a version string |
| `NoCompletedTasks` | No tasks marked complete in the specified range | Verify task status or broaden the version range |
| `ChangelogNotFound` | Changelog file path does not exist | Create a CHANGELOG.md or specify the correct path |
| `GitHistoryUnavailable` | Not a git repo or git not installed | Release notes will be built from tasks only, without PR data |

## Dependencies

- Completed tasks from the Seed Tasks / task management workflow
- Git history (optional) for PR and merge data
- Existing CHANGELOG.md for appending
- DevOps/Release Engineer persona's template if available
