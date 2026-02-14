# Skill: Trello Load

## Description

Connects to Trello via the MCP server, pulls all cards from the Sprint_Backlog
list, and creates well-formed beans directly from each card's content. Beans are
created with **Approved** status (ready for work). After each bean is created,
the source card is moved to the In_Progress list on Trello. This runs fully
non-interactively — no user prompts, no clarifying questions — suitable for
cron jobs or automated pipelines like `/long-run`.

## Trigger

- Invoked by the `/trello-load` slash command.
- Requires the Trello MCP server to be configured and accessible.
- Requires `ai/beans/_index.md` and `ai/beans/_bean-template.md` to exist.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| board_id | String | No | If provided via `--board`, use that board. Otherwise auto-detect (see below). |
| dry_run | Boolean | No | If true, show cards and proposed beans without creating them. Defaults to false. |

## Process

### Phase 1: Board Selection (Automatic)

1. **Check Trello connection** — Call `mcp__trello__get_health` to verify the
   MCP server is responsive. If unhealthy, report the error and stop.

2. **Determine board** — Three strategies, in order:
   a. If `--board <id>` was provided, use that board ID directly.
   b. Call `mcp__trello__list_boards` and look for a board whose name matches
      the current project directory name (case-insensitive). For this repo,
      that means a board named "Foundry".
   c. If no match, use the first board returned.
   Log which board was selected and why.

3. **Set active board** — Call `mcp__trello__set_active_board` with the
   resolved board ID.

### Phase 2: List Discovery

5. **Fetch lists** — Call `mcp__trello__get_lists` for the selected board.

6. **Find Sprint_Backlog list** — Search the returned lists for one matching
   "Sprint_Backlog" using flexible matching:
   - Normalize both the target name and each list name by:
     - Converting to lowercase
     - Replacing underscores, hyphens, and spaces with a single common separator
   - Match if the normalized names are equal
   - Examples that match: "Sprint_Backlog", "sprint_backlog", "Sprint Backlog",
     "sprint-backlog", "SPRINT_BACKLOG"
   - If no match found, show available list names and stop with an error.

7. **Find In_Progress list** — Same flexible matching for "In_Progress":
   - Matches: "In_Progress", "in_progress", "In Progress", "in-progress",
     "IN_PROGRESS"
   - If no match found, show available list names and stop with an error.

8. **Report discovered lists** — Confirm to the user:
   ```
   Found lists:
   - Sprint Backlog: "[actual list name]" (N cards)
   - In Progress: "[actual list name]"
   ```

### Phase 3: Card Loading

9. **Fetch cards** — Call `mcp__trello__get_cards_by_list_id` with the
   Sprint_Backlog list ID.

10. **Check for empty backlog** — If no cards are returned, inform the user
    and stop:
    ```
    Sprint_Backlog is empty — nothing to process.
    ```

11. **Fetch full card details** — For each card, gather complete data:
    a. **Card details** — Call `mcp__trello__get_card` with `includeMarkdown: true`
       to get name and description.
    b. **Checklists** — For each checklist on the card, call
       `mcp__trello__get_checklist_items` to get all checklist items and their
       completion state.
    c. **Comments** — Call `mcp__trello__get_card_comments` to get all comments.

12. **Compile card text** — For each card, assemble a single text block:
    ```
    # [Card Name]

    ## Description
    [Card description text]

    ## Checklists
    ### [Checklist Name]
    - [x] Completed item
    - [ ] Incomplete item
    ...

    ## Comments
    - [Author] ([date]): [comment text]
    ...
    ```
    Omit sections that are empty (e.g., if no checklists, skip that section).

13. **Log summary** — Show what will be processed:
    ```
    Found N cards in Sprint_Backlog:
    1. [Card Name] — [first 80 chars of description]
    2. [Card Name] — [first 80 chars of description]
    ...

    Creating beans and moving cards to In_Progress.
    ```

14. **Handle dry run** — If `dry_run` is true, show the compiled text and
    proposed bean fields for each card and stop. Do not create beans or move
    any cards.

### Phase 4: Sequential Bean Creation (Non-Interactive)

15. **Process each card** — For each card in order:

    a. **Announce** — Log which card is being processed:
       ```
       --- Processing card 1/N: [Card Name] ---
       ```

    b. **Re-read `ai/beans/_index.md`** to get the current max bean ID.
       Another agent may have added beans since the last read.

    c. **Assign the next sequential ID** (max + 1).

    d. **Create the bean directly** — Build a well-formed bean from the card
       content. Do NOT invoke `/backlog-refinement` — create the bean inline
       to avoid interactive dialogue. Map card fields to bean fields:

       - **Title:** Use the card name. Generate a slug from it.
       - **Problem Statement:** Derive from the card description. If the
         description is empty, expand the card name into a problem statement
         (e.g., "Create a test that..." → "The project lacks an end-to-end
         test that...").
       - **Goal:** Infer the desired outcome from the description and any
         checklists.
       - **Scope — In Scope:** Extract from checklist items and description.
         If sparse, infer reasonable scope from the title.
       - **Scope — Out of Scope:** Use best judgment to set boundaries.
       - **Acceptance Criteria:** Convert checklist items to acceptance
         criteria. Always include the standard "All tests pass" and "Lint
         clean" criteria. Ensure at least 3 total criteria.
       - **Priority:** Default to High (sprint backlog items are prioritized).
         If the card has labels, use them as hints (red=High, yellow=Medium,
         green=Low).
       - **Status:** **Approved** (not Unapproved — these come from a
         curated sprint backlog and are pre-approved).
       - **Category:** Infer from content (App for code/test/UI changes,
         Process for workflow/agent changes, Infra for CI/CD/git changes).
       - **Notes:** Include "Source: Trello card '[Card Name]'" and a link
         to the card URL.

    e. **Write the bean** — Create `ai/beans/BEAN-NNN-<slug>/bean.md` and
       append to `_index.md` immediately.

    f. **Move card to In_Progress** — Call `mcp__trello__move_card` with the
       card ID and the In_Progress list ID. Log the move:
       ```
       Moved "[Card Name]" → In_Progress | Created BEAN-NNN
       ```

    g. **Handle errors gracefully** — If bean creation or card move fails:
       - Log the error
       - Skip the card, leave it in Sprint_Backlog
       - Continue to the next card (do not stop)

### Phase 5: Summary

16. **Present completion report** — After all cards are processed (or processing
    is stopped early), show:
    ```
    Trello Load Complete:
    - Cards processed: N/M
    - Cards moved to In_Progress: N
    - Cards skipped: N
    - Total beans created: N

    Created beans:
    | Bean ID | Title | Source Card |
    |---------|-------|-------------|
    | BEAN-NNN | [title] | [card name] |
    ...
    ```

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| new_beans | Markdown files | Beans created directly from each card's content |
| updated_index | Markdown file | `_index.md` updated with all new beans |
| trello_moves | Trello API | Cards moved from Sprint_Backlog to In_Progress |
| summary | Console text | Completion report with counts and bean-to-card mapping |

## Quality Criteria

- Every card's full context (name, description, checklists, comments) is used
  to populate the bean — no data is silently dropped.
- List name matching is flexible and case-insensitive.
- Cards are only moved to In_Progress after bean creation succeeds.
- If bean creation fails for a card, it stays in Sprint_Backlog.
- Beans are created with **Approved** status (pre-approved from sprint backlog).
- No user interaction required — the entire flow runs autonomously.
- Clear progress logging (card N/M) throughout processing.
- The final summary accurately reflects what was created and moved.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `TrelloMCPDown` | Trello MCP server not responding | Log error, stop |
| `NoBoards` | No boards accessible via the API | Log error, stop |
| `ListNotFound` | Sprint_Backlog or In_Progress list not found | Log available list names, stop |
| `EmptyBacklog` | Sprint_Backlog has no cards | Log message, stop (not an error) |
| `CardFetchError` | Failed to fetch details for a specific card | Log warning, skip card, continue |
| `BeanCreateError` | Failed to create bean for a card | Log error, skip card, continue |
| `MoveError` | Failed to move a card to In_Progress | Log warning, card stays in Sprint_Backlog, continue |

## Dependencies

- Trello MCP server (configured and accessible)
- `mcp__trello__list_boards`, `mcp__trello__get_lists`, `mcp__trello__get_cards_by_list_id`
- `mcp__trello__get_card`, `mcp__trello__get_card_comments`, `mcp__trello__get_checklist_items`
- `mcp__trello__move_card`
- Backlog index at `ai/beans/_index.md`
- Bean template at `ai/beans/_bean-template.md`
