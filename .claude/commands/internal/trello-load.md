# /trello-load Command

Connects to Trello via the MCP server, pulls all cards from a board's
Sprint_Backlog list, and creates well-formed beans directly from each card's
content. Beans are created with **Approved** status. After each bean is created,
the source card is moved to In_Progress on Trello.

**IMPORTANT:** This command creates beans inline — it does NOT route through
`/backlog-refinement`. This is required to preserve Trello metadata (Card ID,
Board) in the bean's `## Trello` section, which `/long-run` uses to move cards
to Completed when work finishes.

## Usage

```
/trello-load
/trello-load --board <id>
/trello-load --dry-run
```

Runs non-interactively when called by `/long-run`. See
`.claude/skills/internal/trello-load/SKILL.md` for the full process specification.

## Critical: Trello Section

Every bean created from a Trello card MUST have a fully populated `## Trello`
section — not the template default of `Source: Manual`. The correct format:

```markdown
## Trello

| Field | Value |
|-------|-------|
| **Source** | Trello |
| **Board** | [board name] (ID: [board ID]) |
| **Source List** | Sprint_Backlog |
| **Card ID** | [card ID from API] |
| **Card Name** | [card name] |
| **Card URL** | [card URL] |
```

Without this, `/long-run` cannot move the card to Completed when the bean is done.
