# /trello-load Command

Claude Code slash command that connects to Trello, pulls cards from a board's
Sprint_Backlog list, and feeds each card into `/backlog-refinement` to create
well-formed beans. Cards are moved to In_Progress after refinement.

## Purpose

Bridges Trello sprint planning with the beans workflow. Instead of manually
copying card descriptions into `/backlog-refinement`, this command pulls them
directly from Trello, processes each card through the refinement dialogue, and
updates the card's status on the board automatically.

## Usage

```
/trello-load
```

No arguments required — the command prompts for board selection interactively.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Board selection | Interactive prompt (Trello MCP) | Yes |
| Sprint_Backlog list | Auto-discovered from selected board (flexible name match) | Yes |
| In_Progress list | Auto-discovered from selected board (flexible name match) | Yes |
| Card data | Trello cards: name, description, checklists, comments | Yes |
| Backlog | `ai/beans/_index.md` | Yes (passed to `/backlog-refinement`) |

## Process

1. **Connect to Trello** — Use the Trello MCP server to list all available boards.
2. **Select board** — Present the board list and ask the user which board to use.
3. **Discover lists** — Fetch all lists from the selected board. Find the
   Sprint_Backlog and In_Progress lists using flexible name matching
   (case-insensitive, treating underscores/spaces/hyphens as equivalent).
4. **Load cards** — Pull all cards from the Sprint_Backlog list. For each card,
   fetch full details including name, description, checklists (with items), and
   comments.
5. **Show summary** — Display the cards that will be processed:
   ```
   Found N cards in Sprint_Backlog:
   1. [Card Name] — [first line of description]
   2. [Card Name] — [first line of description]
   ...
   Processing each card through /backlog-refinement sequentially.
   ```
6. **Process each card** — For each card, sequentially:
   a. Compile the card's full text (name + description + checklist items +
      comments) into a single block of text.
   b. Pass that text to `/backlog-refinement` as the raw_text input.
   c. After `/backlog-refinement` completes, move the Trello card from
      Sprint_Backlog to In_Progress.
   d. Confirm the move to the user before proceeding to the next card.
7. **Final summary** — After all cards are processed, show a completion summary:
   ```
   Trello Load Complete:
   - N cards processed through /backlog-refinement
   - N cards moved to In_Progress
   - N beans created (total)
   ```

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| New beans | `ai/beans/BEAN-NNN-<slug>/bean.md` | Beans created via `/backlog-refinement` |
| Updated index | `ai/beans/_index.md` | All new beans added to the backlog |
| Trello updates | Trello board | Cards moved from Sprint_Backlog to In_Progress |
| Summary | Console output | Completion report with counts |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `false` | Show which cards would be processed without creating beans or moving cards |
| `--board <id>` | None | Skip board selection and use the specified board ID directly |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoBoards` | No Trello boards accessible | Check Trello MCP server connection and API key |
| `ListNotFound` | No Sprint_Backlog or In_Progress list on the board | Warn user and list available list names so they can create the missing list |
| `EmptyBacklog` | Sprint_Backlog list has no cards | Inform user — nothing to process |
| `TrelloMCPDown` | Trello MCP server not responding | Check MCP server configuration and restart if needed |
| `RefinementAbort` | User cancels during a `/backlog-refinement` dialogue | Card stays in Sprint_Backlog; continue to next card or stop (ask user) |

## Examples

**Basic usage:**
```
/trello-load
```
Lists boards, user picks one, processes all Sprint_Backlog cards through
`/backlog-refinement`, moves each to In_Progress.

**Dry run:**
```
/trello-load --dry-run
```
Shows which cards would be loaded without creating beans or moving cards.

**Direct board:**
```
/trello-load --board 698e9e614a5e03d0ed57f638
```
Skips board selection and loads from the specified board directly.
