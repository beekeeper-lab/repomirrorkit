# /bean-status Command

Claude Code slash command that displays the current state of the beans backlog — a quick snapshot of what's unapproved, approved, in progress, and done.

## Purpose

Provides a readable summary of the beans backlog without having to open and parse `_index.md` manually. Useful for the Team Lead during sprint planning, retrospectives, or when deciding which bean to pick next.

## Usage

```
/bean-status [--filter <status>] [--verbose]
```

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Status filter | `--filter` flag | No (shows all by default) |
| Verbose mode | `--verbose` flag | No |

## Process

1. **Read index** -- Parse `ai/beans/_index.md` and extract the backlog table.
2. **Read bean details** -- For each bean, read its `bean.md` to get the tasks table and acceptance criteria status.
3. **Categorize** -- Group beans by status: In Progress, Approved, Unapproved, Deferred, Done.
4. **Format summary** -- Display:
   - Counts by status (e.g., "3 Done, 1 In Progress, 2 Approved, 1 Unapproved")
   - Table of beans with ID, Title, Priority, Status, Owner
   - If `--verbose`: include task breakdown for In Progress beans (how many tasks done vs total)
5. **Highlight actionable items** -- Flag beans that are `Approved` and ready to pick, `Unapproved` and awaiting review, or `In Progress` with all tasks done (ready to close).

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Status summary | stdout | Formatted backlog summary displayed in the conversation |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--filter <status>` | All | Show only beans with this status: `unapproved`, `approved`, `in-progress`, `done`, `deferred` |
| `--verbose` | `false` | Include task-level detail for active beans |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `IndexNotFound` | `ai/beans/_index.md` does not exist | No beans backlog — scaffold the project or create it manually |
| `EmptyBacklog` | Index exists but has no beans | Create beans with `/new-bean` |

## Examples

**Full backlog overview:**
```
/bean-status
```
Displays all beans grouped by status with counts.

**Only in-progress beans with task detail:**
```
/bean-status --filter in-progress --verbose
```
Shows only active beans with their task breakdown (e.g., "3/4 tasks done").

**Only approved beans ready for picking:**
```
/bean-status --filter approved
```
Shows beans available for the Team Lead to pick.

**Only unapproved beans awaiting review:**
```
/bean-status --filter unapproved
```
Shows beans that need human review before they can be executed.
