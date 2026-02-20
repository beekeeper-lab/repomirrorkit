# /new-dev-decision Command

Claude Code slash command that records a lightweight developer decision.

## Purpose

Capture implementation-level decisions that matter but don't warrant a full ADR. Library choices, algorithm approaches, error handling strategies, performance tradeoffs — the decisions that make a future developer ask "why did we do it this way?" This creates a searchable decision log so the answer is always one grep away.

## Usage

```
/new-dev-decision "<title>" [--context <text>] [--alternatives <list>] [--tags <list>]
```

- `title` -- Short title for the decision (required).

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Title | Positional argument | Yes |
| Context | `--context` flag or interactive prompt | Yes (prompted if omitted) |
| Decision | `--chosen` flag or interactive prompt | Yes (prompted if omitted) |
| Alternatives | `--alternatives` flag | No |
| Tags | `--tags` flag | No |
| Work ID | `--work` flag | No |

## Process

1. **Assign number** -- Auto-increment from existing dev decisions.
2. **Capture decision** -- Record title, context, choice, rationale, alternatives, and consequences.
3. **Write file** -- Save as `DD-{NNN}-{slug}.md`.
4. **Update log** -- Append to the decision log if one exists.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Decision record | `ai/outputs/developer/decisions/DD-{NNN}-{slug}.md` | Lightweight decision record |
| Log update | `ai/outputs/developer/decisions/decision-log.md` (appended) | One-line index entry |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--context <text>` | Interactive prompt | Why the decision was needed |
| `--chosen <text>` | Interactive prompt | What was decided and why |
| `--alternatives <list>` | None | Comma-separated alternatives considered |
| `--tags <list>` | None | Comma-separated tags (e.g., `performance,caching`) |
| `--work <id>` | None | Related work item ID |
| `--output <dir>` | `ai/outputs/developer/decisions/` | Override the output directory |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyTitle` | No title provided | Supply a decision title |
| `EmptyContext` | No context provided | Describe why the decision was needed |
| `EmptyChosen` | No decision stated | State what was chosen |

## Examples

**Quick decision:**
```
/new-dev-decision "Use dataclasses instead of TypedDict for DTOs"
```
Prompts for context and rationale interactively. Writes `DD-001-use-dataclasses-instead-of-typeddict-for-dtos.md`.

**Fully inline:**
```
/new-dev-decision "Cache user sessions in Redis" --context "Session lookups hitting the DB on every request, adding 40ms latency" --chosen "Redis with 30-minute TTL — gives us sub-millisecond lookups and natural expiry" --alternatives "In-memory cache (lost on restart), DB with index (still 5ms)" --tags performance,caching --work WRK-007
```
Creates a complete decision record without interactive prompts.

**Tagged for searchability:**
```
/new-dev-decision "Use structured logging with JSON output" --tags logging,observability
```
Decision is tagged so future searches for "logging" or "observability" find it.

## When to Use This vs /internal:new-adr

| Use `/new-dev-decision` when... | Use `/internal:new-adr` when... |
|------|------|
| The decision is implementation-level | The decision is architectural |
| It affects one component or module | It affects system boundaries or multiple components |
| The Developer made the choice | The Architect made the choice |
| A one-screen record is sufficient | Full options analysis with pros/cons is needed |
| Examples: library choice, algorithm, data structure | Examples: database engine, API style, deployment topology |
