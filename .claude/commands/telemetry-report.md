# /telemetry-report Command

Produces an aggregate summary of project telemetry: total time invested, average bean duration, breakdowns by category and owner, and outlier identification.

## Usage

```
/telemetry-report [--category <cat>] [--status <status>] [--since YYYY-MM-DD]
```

- `--category <cat>` -- Filter by category: `App`, `Process`, `Infra`. Case-insensitive.
- `--status <status>` -- Filter by bean status. Default: `Done`. Use `all` for everything.
- `--since YYYY-MM-DD` -- Only include beans created on or after this date.

## Process

See `.claude/skills/telemetry-report/SKILL.md` for the full skill specification.

## Examples

**Full report (all Done beans):**
```
/telemetry-report
```

**App beans only:**
```
/telemetry-report --category App
```

**Everything since Feb 9:**
```
/telemetry-report --since 2026-02-09
```
