# /new-adr Command

Claude Code slash command that creates a new Architecture Decision Record.

## Purpose

Document a significant technical or architectural decision with context, options, tradeoffs, rationale, and consequences. ADRs create a searchable decision history so the team understands *why* the codebase looks the way it does -- not just *what* it does.

## Usage

```
/new-adr "<decision title>" [--context <text-or-file>] [--related <item-ids>]
```

- `decision title` -- Short title for the decision (required).

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Decision title | Positional argument | Yes |
| Context | `--context` flag, inline text, or interactive prompt | Yes (prompted if omitted) |
| Options | Interactive prompt | Prompted during execution |
| Related items | `--related` flag | No |

## Process

1. **Assign ADR number** -- Auto-increment from the highest existing ADR.
2. **Capture context and options** -- Prompt for problem statement and at least two options with pros/cons.
3. **Record decision and consequences** -- Document the chosen option, rationale, and impacts.
4. **Write ADR file** -- Save as `adr-{NNN}-{slug}.md`.
5. **Update index** -- Append to ADR index if one exists.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| ADR file | `ai/context/decisions/adr-{NNN}-{slug}.md` | Complete decision record |
| Index update | `ai/context/decisions.md` (appended) | New entry in the decisions index |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--context <text>` | Interactive prompt | Provide context inline instead of being prompted |
| `--related <ids>` | None | Comma-separated story/task/issue IDs related to this decision |
| `--output <dir>` | `ai/context/decisions/` | Override the ADR output directory |
| `--template <path>` | Architect's ADR template | Custom ADR template to use |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyTitle` | No title provided | Supply a decision title as the first argument |
| `AdrDirNotWritable` | Cannot write to the output directory | Check permissions |

## Examples

**Create a new ADR interactively:**
```
/new-adr "Use PostgreSQL for primary datastore"
```
Prompts for context, options, and rationale. Writes `adr-001-use-postgresql-for-primary-datastore.md`.

**Create with inline context:**
```
/new-adr "Adopt monorepo structure" --context "The team needs to share code between frontend and backend. Currently using separate repos which causes version drift." --related STORY-003,STORY-007
```
Creates the ADR with pre-filled context and linked stories.

**Custom output directory:**
```
/new-adr "Switch from REST to GraphQL" --output docs/decisions/
```
Writes the ADR to `docs/decisions/` instead of the default location.
