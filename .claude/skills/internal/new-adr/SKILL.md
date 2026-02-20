# Skill: New ADR

## Description

Creates a new Architecture Decision Record from a structured template. Guides
the author through capturing the context, decision drivers, considered options
with tradeoffs, the chosen option with rationale, and consequences. Links the
ADR to related stories or work items and assigns it a sequential number.
This skill enforces ADR discipline so that architectural decisions are documented
consistently and discoverable by the whole team.

## Trigger

- Invoked by the `/new-adr` slash command.
- Called by the Architect persona when a significant design decision is made.
- Can be invoked by any persona when a technical decision warrants formal documentation.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| decision_title | String | Yes | Short title for the decision (e.g., "Use PostgreSQL for primary datastore") |
| context | Text | Yes | Background and problem statement driving the decision |
| options | List of strings | No | Options considered; the skill will prompt for these if omitted |
| related_items | List of strings | No | Story IDs, task IDs, or issue references this decision relates to |
| adr_dir | Directory path | No | Where to write ADRs; defaults to `ai/context/decisions/` or `ai/outputs/architect/` |

## Process

1. **Determine next ADR number** -- Scan the ADR directory for existing `adr-NNN-*.md` files and increment the highest number found. If no ADRs exist, start at 001.
2. **Capture context** -- Record the problem statement, constraints, and forces driving the decision. Include relevant technical and business context.
3. **Document options** -- For each considered option, record:
   - Description of the approach
   - Pros (advantages, strengths)
   - Cons (disadvantages, risks, costs)
   - Feasibility assessment
4. **Record the decision** -- State which option was chosen and the rationale. The rationale must reference specific pros/cons from the options analysis.
5. **Document consequences** -- List positive consequences (what improves), negative consequences (what gets harder or more expensive), and neutral consequences (what changes without clear value judgment).
6. **Link related items** -- Add references to stories, tasks, or issues that motivated or are affected by this decision.
7. **Write the ADR file** -- Save as `adr-{NNN}-{slug}.md` in the ADR directory.
8. **Update the ADR index** -- If an `adr-index.md` or `decisions.md` file exists, append the new entry.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| adr_file | Markdown file | The complete ADR following the project template |
| adr_index_update | Appended text | New entry added to the ADR index if one exists |

## Quality Criteria

- The ADR number is unique and sequential with no gaps or collisions.
- The context section explains *why* a decision was needed, not just *what* was decided.
- At least two options are documented (including the chosen one) with genuine pros and cons.
- The rationale explicitly connects to the pros/cons analysis rather than stating a preference without evidence.
- Consequences distinguish between positive, negative, and neutral impacts.
- The ADR is self-contained: a reader unfamiliar with the project can understand the decision and its reasoning.
- The slug in the filename is a kebab-case summary of the title.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyTitle` | No decision title provided | Supply a concise title for the decision |
| `EmptyContext` | No context or problem statement provided | Describe why the decision is needed |
| `AdrDirNotWritable` | Cannot write to the ADR directory | Check permissions or specify a different directory |
| `DuplicateTitle` | An ADR with a very similar title already exists | Review the existing ADR; amend it or use a distinct title |

## Dependencies

- Architect persona's ADR template (`personas/architect/templates/adr.md`) if available
- Access to the ADR directory for numbering
- No other skills are required; ADRs can be created at any point in the project
