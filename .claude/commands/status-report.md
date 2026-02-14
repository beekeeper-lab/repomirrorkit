# /status-report Command

Claude Code slash command that generates a status report summarizing current progress, blockers, and next steps across the team.

## Purpose

Produce a structured status report by scanning the project workspace for task states, completed artifacts, and outstanding blockers. The report gives the Team Lead (and stakeholders) a single-document view of where the project stands without manually assembling updates from each persona. Output follows the status report template from `personas/team-lead/templates/status-report.md`.

## Usage

```
/status-report [--format brief|full] [--cycle current|all]
```

All arguments are optional. With no flags, the command produces a full report for the current cycle.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Task files | `ai/tasks/*.md` in the project workspace | Yes |
| Team composition | `composition.yml` or compiled `CLAUDE.md` | Yes |
| Report template | `personas/team-lead/templates/status-report.md` | No (uses built-in format if absent) |
| Prior reports | `ai/reports/status-*.md` | No (used for velocity calculation) |
| Decision log | `ai/decisions/decision-log.md` | No (included if present) |

## Process

1. **Scan task state** -- Read all task files in `ai/tasks/`. Classify each as completed, in-progress, blocked, or not-started based on its status field and checklist completion.
2. **Collect artifact summaries** -- For each persona with completed tasks, summarize the artifacts produced (files written, templates filled, reviews conducted). Reference file paths rather than duplicating content.
3. **Identify blockers and dependencies** -- Extract blocked items and their stated blockers. Cross-reference with dependency graph to find cascading impacts.
4. **Calculate velocity metrics** -- Compare current cycle progress against prior reports (if available). Compute: tasks completed this cycle, tasks added, tasks carried over, completion rate as a percentage.
5. **Gather decisions and escalations** -- Pull recent entries from the decision log and any open escalation items.
6. **Generate report** -- Populate the status report template with all collected data. Include the metadata header, summary, completed/in-progress/blocked tables, risks, and next-period plan.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Status report | `ai/reports/status-{cycle}-{date}.md` | Completed report following the Team Lead template |
| Velocity snapshot | Embedded in report | Task throughput metrics for the current cycle |

The report structure follows `personas/team-lead/templates/status-report.md`:
- **Metadata** -- Date, owner, period, status
- **Summary** -- Two to three sentence overview
- **Completed Items** -- Deliverables finished and accepted
- **In Progress Items** -- Active work with owner, percent done, ETA
- **Blocked Items** -- Stalled items with blocker identification
- **Decisions Made** -- References to decision log entries
- **Risks and Escalations** -- New or changed risks with severity
- **Next Period Plan** -- Top priorities for the upcoming period

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--format <brief\|full>` | `full` | `brief` produces a condensed summary (summary + blockers + next steps only); `full` includes all sections |
| `--cycle <current\|all\|label>` | `current` | Scope the report to a specific cycle or show cumulative progress |
| `--output <path>` | `ai/reports/` | Override the output directory for the report |
| `--include-velocity` | `true` | Include velocity metrics (disable with `--no-velocity` if no prior reports exist) |
| `--dry-run` | `false` | Display the report to stdout without writing a file |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoTasksFound` | No task files exist in `ai/tasks/` | Run `/seed-tasks` first to create the initial task set |
| `NoTeamComposition` | Neither composition spec nor compiled CLAUDE.md found | Run `/compile-team` first |
| `MalformedTaskFile` | A task file cannot be parsed (missing status field, broken markdown) | Fix the task file format; ensure it has a status field |
| `NoPriorReports` | Velocity calculation requested but no prior reports exist | First report of a project will skip velocity or show baseline-only metrics |
| `OutputDirNotWritable` | Cannot write to the reports directory | Check permissions and that the directory exists |

## Examples

**Generate a full status report for the current cycle:**
```
/status-report
```
Scans all tasks, collects progress, and writes a full report to `ai/reports/status-cycle-1-2025-01-15.md`.

**Generate a brief summary:**
```
/status-report --format brief
```
Produces a condensed report with just the summary, blockers, and next steps -- useful for quick standups.

**Report across all cycles:**
```
/status-report --cycle all --include-velocity
```
Generates a cumulative report covering all cycles with velocity trends showing throughput over time.

**Preview without writing:**
```
/status-report --dry-run --format full
```
Displays the full report in the terminal without writing a file. Useful for reviewing before committing.
