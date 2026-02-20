# Skill: Commands

## Description

Prints a quick-reference table of all available slash commands with usage and flags.
This skill makes NO tool calls — it outputs a hardcoded table for instant response.

## Trigger

- Invoked by the `/commands` slash command.

## Process

**Immediately print the following table. Do not call any tools. Do not read any files.**

```
| Command | Usage | Flags | Description |
|---------|-------|-------|-------------|
| `/trello-add` | `/trello-add <text>` | `--sprint`, `--label <color>` | Create a Trello card (first line = name, rest = description) |
| `/trello-load` | `/trello-load` | `--board <id>`, `--dry-run` | Pull Sprint_Backlog cards into beans |
| `/backlog-refinement` | `/backlog-refinement <text>` | `--dry-run` | Turn free-form ideas into beans via dialogue |
| `/backlog-consolidate` | `/backlog-consolidate` | `--status <s>`, `--dry-run` | Detect duplicates/overlaps across beans |
| `/show-backlog` | `/show-backlog` | `--status <s>`, `--category <c>` | Display bean backlog as a table |
| `/review-beans` | `/review-beans` | `--status <s>`, `--category <c>` | Open beans in Obsidian for review/approval |
| `/long-run` | `/long-run` | `--fast N`, `--category <c>` | Autonomous bean processing (sequential or parallel) |
| `/deploy` | `/deploy [target]` | `--tag <version>` | Promote test→main (or branch→test) via PR |
| `/run` | `/run [branch]` | _(none)_ | Pull latest code and launch the Foundry app |
| `/status-report` | `/status-report` | `--format brief\|full`, `--cycle <c>` | Generate a project status report |
| `/telemetry-report` | `/telemetry-report` | `--category <c>`, `--status <s>`, `--since <date>` | Aggregate time/duration telemetry across beans |
| `/docs-update` | `/docs-update` | `--dry-run` | Audit project docs against codebase, fix stale values |
| `/bg` | `/bg <command> [args]` | _(passes flags to inner command)_ | Run any slash command in a background tmux window |
| `/commands` | `/commands` | _(none)_ | This table |
```

That is the complete output. Do not add commentary before or after the table.

## Quality Criteria

- Zero tool calls — print the table directly from this spec.
- Table must render cleanly in a monospace terminal.
- Keep it to one line per command — compact reference, not documentation.
