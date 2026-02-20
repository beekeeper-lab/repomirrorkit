# Skill: Trello Add

## Description

Creates a Trello card from the command line. The first line of input becomes the
card name; any remaining lines become the card description. Cards go to the
Backlog list by default; use `--sprint` to target Sprint_Backlog instead. An
optional `--label <color>` flag applies a board label by color name.

## Trigger

- Invoked by the `/trello-add` slash command.
- Requires the Trello MCP server to be configured and accessible.

## Usage

```
/trello-add Fix the validator error message
/trello-add --sprint Urgent hotfix for seeder
/trello-add --label red Urgent: pipeline broken on main
/trello-add --sprint --label green Add retry logic to compiler
/trello-add Multi-line card title
This is the description that goes on the card.
It can span multiple lines.
```

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| text | String | Yes | First line = card name, remaining lines = description |
| `--sprint` | Flag | No | Route card to Sprint_Backlog instead of Backlog |
| `--label <color>` | String | No | Apply a board label by color name (e.g., red, green, blue) |

## Process

### Phase 1: Parse Input

1. **Extract flags** from the input text:
   - If `--sprint` is present, remove it and set target list to "Sprint_Backlog".
     Otherwise target list is "Backlog".
   - If `--label <color>` is present, remove both the flag and its value. Store
     the color name for Phase 3.
2. **Split remaining text** into name and description:
   - First line (after flag removal and trimming) = card name.
   - All subsequent lines (if any) = card description.
3. **Validate** that the card name is not empty. If empty, report an error and stop.

### Phase 2: Board + List Discovery

4. **Find the board** — Call `mcp__trello__list_boards` and look for a board
   whose name matches "Foundry" (case-insensitive). If no match, use the first
   board returned. Log which board was selected.

5. **Set active board** — Call `mcp__trello__set_active_board` with the resolved
   board ID.

6. **Fetch lists** — Call `mcp__trello__get_lists` for the selected board.

7. **Find target list** — Search the returned lists for the target list name
   using flexible matching (same as `/trello-load`):
   - Normalize both the target name and each list name by:
     - Converting to lowercase
     - Replacing underscores, hyphens, and spaces with a single common separator
   - Match if the normalized names are equal
   - For "Backlog": matches "Backlog", "backlog", "BACKLOG"
   - For "Sprint_Backlog": matches "Sprint_Backlog", "sprint_backlog",
     "Sprint Backlog", "sprint-backlog"
   - If no match found, show available list names and stop with an error.

### Phase 3: Resolve Label (if requested)

8. **If `--label` was provided:**
   - Call `mcp__trello__get_board_labels` for the board.
   - Find the label whose color matches the requested color (case-insensitive).
   - If no match, warn the user (list available colors) and create the card
     without a label rather than failing.

### Phase 4: Create Card

9. **Create card** — Call `mcp__trello__add_card_to_list` with:
   - `listId`: the resolved target list ID
   - `name`: the card name
   - `description`: the card description (if any)
   - `labels`: array containing the resolved label ID (if any)

10. **Report success** — Print:
    ```
    Created: "[card name]" → [list name]
    https://trello.com/c/[shortLink]
    ```
    The card URL is available from the `add_card_to_list` response (`shortUrl` or
    constructed from `shortLink`).

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| trello_card | Trello API | New card created in the target list |
| summary | Console text | Card name, target list, and clickable URL |

## Quality Criteria

- Card name is never empty — validated before API call.
- List name matching is flexible and case-insensitive.
- Label mismatch is a warning, not a fatal error.
- Card URL is always printed so the user can click through to Trello.
- No user interaction required — runs fully non-interactively.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyInput` | No text provided after flag parsing | Report error: "Provide a card name" |
| `NoBoards` | No boards accessible via the API | Log error, stop |
| `ListNotFound` | Target list not found on the board | Show available list names, stop |
| `LabelNotFound` | Requested label color not on the board | Warn, create card without label |
| `CreateFailed` | Trello API error creating the card | Report the error |

## Dependencies

- Trello MCP server (configured and accessible)
- `mcp__trello__list_boards`, `mcp__trello__set_active_board`
- `mcp__trello__get_lists`, `mcp__trello__add_card_to_list`
- `mcp__trello__get_board_labels` (only when `--label` is used)
