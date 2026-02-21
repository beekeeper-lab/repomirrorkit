# Skill: New Dev Decision

## Description

Creates a lightweight developer decision record for implementation-level
choices that don't rise to the level of a full ADR. Where ADRs capture
architectural decisions (database choice, service boundaries, API strategy),
dev decisions capture the smaller but still important choices made during
implementation: library selection, algorithm approach, data structure choice,
error handling strategy, or performance tradeoff. These decisions accumulate
into a searchable log that prevents the "why did we do it this way?" question
from going unanswered.

## Trigger

- Invoked by the `/new-dev-decision` slash command.
- Called by the Developer persona during implementation when a non-trivial choice is made.
- Can be invoked by any persona making an implementation-level decision.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| title | String | Yes | Short title for the decision (e.g., "Use dataclasses instead of TypedDict for DTOs") |
| context | Text | Yes | Why the decision was needed — what problem or tradeoff was encountered |
| chosen | Text | Yes | What was decided and a brief rationale |
| alternatives | List of strings | No | Other options considered (brief — not the full pros/cons of an ADR) |
| work_id | String | No | Work item ID this decision relates to |
| tags | List of strings | No | Tags for categorization (e.g., "performance", "testing", "error-handling") |
| decision_dir | Directory path | No | Where to write decisions; defaults to `ai/outputs/developer/decisions/` |

## Process

1. **Determine next decision number** -- Scan the decision directory for existing `DD-{NNN}-*.md` files and increment. If none exist, start at 001.
2. **Capture the decision** -- Write a concise record:
   - **Title**: The decision in one line.
   - **Date**: Current date.
   - **Context**: Why this came up — the problem, constraint, or tradeoff.
   - **Decision**: What was chosen and the one-paragraph rationale.
   - **Alternatives considered**: Brief list of other options (if provided). Unlike an ADR, a full pros/cons breakdown is not required — a one-liner per alternative is enough.
   - **Consequences**: What this decision means going forward — what's easier, what's harder, what to watch out for.
   - **Tags**: For searchability.
   - **Related work**: Link to the work item if provided.
3. **Write the file** -- Save as `DD-{NNN}-{slug}.md` in the decision directory.
4. **Update decision log** -- If a `decision-log.md` or index file exists in the decision directory, append a one-line entry with the decision number, title, date, and tags.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| decision_file | Markdown file | Lightweight decision record |
| log_update | Appended text | One-line entry in the decision log if one exists |

## Quality Criteria

- The decision record fits on one screen — it should take 30 seconds to read, not 5 minutes. This is the key difference from an ADR.
- Context explains the *why*, not just the *what*. "We needed a way to serialize config" is better than "chose YAML."
- The rationale is specific. "YAML because the config includes comments and nested structures that .env can't express" is good. "YAML because it's better" is not.
- Alternatives list is honest — it shows the decision was considered, not reflexive.
- Consequences focus on what the *next developer* needs to know: gotchas, limitations, things that might need revisiting.
- Tags are consistent across decisions so the log is searchable.
- The decision number is unique and sequential.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyTitle` | No title provided | Supply a concise title for the decision |
| `EmptyContext` | No context provided | Describe why the decision was needed |
| `EmptyChosen` | No decision stated | State what was chosen and why |
| `DecisionDirNotWritable` | Cannot write to the decision directory | Check permissions or specify a different directory |

## Dependencies

- No other skills required — dev decisions can be recorded at any time during implementation
- Developer persona's output directory for default storage location
- No templates required; the format is intentionally lightweight
