# Skill: Long Run

## Description

Puts the Team Lead into autonomous backlog processing mode. The Team Lead reads the bean backlog, selects the best bean to work on, decomposes it into tasks, executes the full team wave, verifies acceptance criteria, commits the result, and loops to the next bean. Continues until no actionable beans remain or an unrecoverable error occurs.

## Trigger

- Invoked by the `/long-run` slash command.
- Should only be used by the Team Lead persona.
- Requires at least one bean in `_index.md` with status `Approved`.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| backlog | Markdown file | Yes | `ai/beans/_index.md` — master bean index |
| bean_workflow | Markdown file | Yes | `ai/context/bean-workflow.md` — lifecycle reference |
| bean_files | Markdown files | Yes | Individual `bean.md` files in `ai/beans/BEAN-NNN-<slug>/` |
| fast | Integer | No | Number of parallel workers. When provided, enables parallel mode via tmux. |
| category | String | No | Filter beans by category: `App`, `Process`, or `Infra`. Case-insensitive. When provided, only beans matching this category are processed. |
| tmux_session | Environment | No | `$TMUX` — required only when `fast` is provided |

## Process

### Phase 0: Branch Prerequisite & Mode Detection

0a. **Ensure on `test` branch** — Run `git branch --show-current`.
   - If already on `test`: proceed.
   - If on `main` with a clean working tree: run `git checkout test` and proceed.
   - If on any other branch or the working tree is dirty: display "⚠ /long-run requires a clean working tree on the `test` branch. Current branch: `<branch>`. Please switch to `test` and retry." Then stop.
0b. **Check mode** — If `fast` input is provided, go to **Parallel Mode** (below). Otherwise, continue with sequential mode (Phase 1).

### Phase 0.5: Trello Sync

0c. **Import sprint backlog from Trello** — Invoke `/trello-load` to pull any
    cards from the Trello Sprint_Backlog list into the beans backlog. This runs
    non-interactively (auto-selects board, creates beans with Approved status,
    moves processed cards to In_Progress on Trello). If the Trello MCP server
    is unavailable or Sprint_Backlog is empty, log the result and continue —
    this step is best-effort and must not block the run.

### Phase 1: Backlog Assessment

1. **Read the backlog index** — Parse `ai/beans/_index.md` to get all beans and their statuses.
2. **Filter actionable beans** — Select beans with status `Approved`. Exclude `Done`, `Deferred`, `Unapproved`, beans blocked by unfinished dependencies, and beans locked by another agent (status `In Progress` with a different Owner). If `category` is provided, further filter to only beans whose Category column matches (case-insensitive).
3. **Check stop condition** — If no actionable beans exist (or none match the category filter), report final summary and exit. If category is active, mention it: "No actionable beans matching category: Process."

### Phase 2: Bean Selection

4. **Read candidate beans** — For each actionable bean, read its `bean.md` to understand priority, scope, dependencies, and notes.
5. **Apply selection heuristics** — Choose the single best bean:
   - **Priority first:** High beats Medium beats Low.
   - **Dependencies second:** If Bean A depends on Bean B (stated in Notes or Scope), select B first.
   - **Logical order third:** Infrastructure and foundational work before features. Data models before UI. Shared utilities before consumers.
   - **ID order last:** Lower bean IDs first as a tiebreaker.
6. **Announce selection** — Print the **Header Block** and **Task Progress Table** from the Team Lead Communication Template (see `.claude/agents/team-lead.md`). If a category filter is active, include it in the header: `[Category: Process]`. This is the first thing visible in the tmux pane.

### Phase 3: Bean Execution

7. **Pick the bean** — Update status to `In Progress` in `bean.md`. Update `_index.md` to set status to `In Progress` and owner to `team-lead`. (In sequential mode the orchestrator is also the worker, so both updates happen here.)
8. **Ensure test branch exists** — Check if `test` branch exists locally. If not, create it: `git checkout -b test main && git checkout -`.
9. **Create feature branch** — Create and checkout the feature branch (mandatory for every bean):
   - Branch name: `bean/BEAN-NNN-<slug>` (derived from the bean directory name)
   - Command: `git checkout -b bean/BEAN-NNN-<slug>`
   - If the branch already exists (e.g., resuming after an error), check it out instead.
   - All work happens on this branch. Never commit to `main`.
10. **Decompose into tasks** — Read the bean's Problem Statement, Goal, Scope, and Acceptance Criteria. Create numbered task files in `ai/beans/BEAN-NNN-<slug>/tasks/`:
    - Name: `01-<owner>-<slug>.md`, `02-<owner>-<slug>.md`, etc.
    - Follow the wave: BA → Architect → Developer → Tech-QA.
    - Skip roles when not needed (e.g., skip BA/Architect for markdown-only beans).
    - Each task file includes: Owner, Depends On, Goal, Inputs, Acceptance Criteria, Definition of Done.
11. **Update bean task table** — Fill in the Tasks table in `bean.md` with the created tasks.

### Phase 4: Wave Execution

12. **Execute tasks in dependency order** — For each task:
    - Record the `Started` timestamp (`YYYY-MM-DD HH:MM`) in the task file metadata when beginning execution.
    - Read the task file and all referenced inputs.
    - Perform the work as the assigned persona.
    - On completion, run the `/close-loop` telemetry recording: record `Completed` timestamp, compute `Duration`, prompt for token self-report, and update the bean's Telemetry per-task table row.
    - Update the task status to `Done` in the task file and the bean's task table.
    - Reprint the **Header Block + Task Progress Table** after each status change.
13. **Skip inapplicable roles** — If a role has no meaningful contribution for a bean (e.g., Architect for a documentation-only bean), skip it. Document the skip reason in the bean's Notes section.

### Phase 5: Verification & Closure

14. **Verify acceptance criteria** — Check every criterion in the bean's Acceptance Criteria section. For code beans: run tests (`uv run pytest`) and lint (`uv run ruff check`).
15. **Close the bean** — Update status to `Done` in `bean.md`. (The orchestrator updates `_index.md` after the merge — see step 17.)
16. **Commit on feature branch** — Stage all files changed during this bean's execution. Commit with message: `BEAN-NNN: <bean title>`. The commit goes on the `bean/BEAN-NNN-<slug>` branch.

### Phase 5.5: Merge Captain

17. **Merge to test branch and update index** — Execute the `/merge-bean` skill to merge the feature branch into `test`:
    - Checkout `test`, pull latest, merge `bean/BEAN-NNN-<slug>` with `--no-ff`, push.
    - If merge conflicts occur: report the conflicts, abort the merge, leave the bean on its feature branch, and stop the loop.
    - If merge succeeds: update `_index.md` to set the bean's status to `Done`, commit the index update on `test`, and push.
17b. **Move Trello card to Completed** — After a successful merge, update the
    source Trello card if one exists:
    a. Check the bean's Notes section for a "Source: Trello card" reference.
    b. If found, call `mcp__trello__get_lists` to find the In_Progress and
       Completed lists (using the same flexible name matching as `/trello-load`).
    c. Call `mcp__trello__get_cards_by_list_id` on the In_Progress list.
    d. Find the card whose name matches the bean title or the card name from
       the Notes reference (case-insensitive, flexible matching).
    e. Call `mcp__trello__move_card` to move the card to the Completed list.
    f. Log the move: `Trello: Moved "[Card Name]" → Completed`
    g. If no matching card is found, or the Trello MCP is unavailable, log a
       warning and continue — this is best-effort and must not block the run.
18. **Stay on test** — Remain on the `test` branch (do not switch to `main`).
19. **Report progress** — Print the **Completion Summary** from the Team Lead Communication Template: bean title, task counts, branch name, files changed, notes, and remaining backlog status.

### Phase 6: Loop

20. **Return to Phase 1** — Read the backlog again. If actionable beans remain, process the next one. If not, report final summary including: `⚠ Work is on the test branch. Run /deploy to promote to main.` Then exit.

---

## Parallel Mode

When `fast N` is provided, the Team Lead orchestrates N parallel workers instead of processing beans sequentially.

### Parallel Phase 1: Prerequisites

1. **Ensure on `test` branch** — Same check as Phase 0a above. Must be on `test` with a clean working tree, or on `main` (auto-checkout to `test`). Otherwise stop.
2. **Check tmux** — Verify `$TMUX` environment variable is set.
   - If not set: display "Parallel mode requires tmux. Please restart Claude Code inside a tmux session and re-run `/long-run --fast N`." Then exit.
   - If set: proceed.

### Parallel Phase 1.5: Trello Sync

1b. **Import sprint backlog from Trello** — Same as sequential Phase 0.5:
    invoke `/trello-load` non-interactively. Best-effort; do not block on
    failure.

### Parallel Phase 2: Backlog Assessment

2. **Read the backlog index** — Same as sequential Phase 1: parse `_index.md`, filter actionable beans with status `Approved` (skip `Unapproved`, locked beans owned by other agents). Apply `category` filter if provided.
3. **Check stop condition** — If no actionable beans (or none matching category), report and exit.
4. **Read candidate beans** — Read each actionable bean's `bean.md` to understand dependencies.

### Parallel Phase 3: Worker Spawning

5. **Select independent beans** — From the actionable set, select up to N beans that have no unmet inter-bean dependencies. Beans that depend on other pending or in-progress beans are queued, not parallelized.
6. **Update bean statuses** — For each selected bean, update `_index.md` to set status to `In Progress` and owner to `team-lead`. Commit this index update on `test` before spawning workers. (Workers will update their own `bean.md` independently; they must NOT touch `_index.md`.)
7. **Write initial status files** — For each selected bean, create a status file at `/tmp/agentic-worker-BEAN-NNN.status` with `status: starting`. This allows the dashboard to track the worker immediately. See the Status File Protocol in `/spawn-bean` for the full file format and status values (`starting`, `decomposing`, `running`, `blocked`, `error`, `done`).
8. **Create worktrees and spawn workers** — For each selected bean, create an isolated git worktree, then create a launcher script and open a tmux child window:
   ```bash
   WORKTREE_DIR="/tmp/agentic-worktree-BEAN-NNN"
   BRANCH_NAME="bean/BEAN-NNN-slug"

   # Clean stale worktree from a prior run
   git worktree remove --force "$WORKTREE_DIR" 2>/dev/null

   # Create feature branch + worktree
   if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
     git worktree add "$WORKTREE_DIR" "$BRANCH_NAME"
   else
     git worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR" main
   fi

   LAUNCHER=$(mktemp /tmp/agentic-bean-XXXXXX.sh)
   cat > "$LAUNCHER" << 'SCRIPT_EOF'
   #!/bin/bash
   cd /tmp/agentic-worktree-BEAN-NNN
   claude --dangerously-skip-permissions --agent team-lead \
     "Process BEAN-NNN-slug through the full team wave.

   You are running in an ISOLATED GIT WORKTREE. Your feature branch is already checked out.
   - Do NOT create or checkout branches.
   - Do NOT run /merge-bean — the orchestrator handles merging after you finish.
   - Do NOT checkout main or test.
   - Do NOT edit _index.md — the orchestrator is the sole writer of the backlog index.

   1. Update bean.md status to In Progress
   2. Decompose into tasks
   3. Execute the wave (BA → Architect → Developer → Tech-QA)
   4. Verify acceptance criteria
   5. Update bean.md status to Done (the PostToolUse telemetry hook auto-computes Duration from git timestamps)
   6. Commit on the feature branch

   STATUS FILE PROTOCOL — You MUST update /tmp/agentic-worker-BEAN-NNN.status at every transition.
   See /spawn-bean command for full status file format and update rules."
   SCRIPT_EOF
   chmod +x "$LAUNCHER"
   tmux new-window -n "bean-NNN" "bash $LAUNCHER; rm -f $LAUNCHER"
   ```
   The prompt is passed as a positional argument to `claude`, so it auto-submits immediately. The window auto-closes when claude exits (no bare shell left behind). The launcher script self-deletes after use. No stagger delay needed — worktrees provide full isolation.
9. **Record worker assignments** — Track which window name maps to which bean, worktree path, and status file.

### Parallel Phase 4: Dashboard Monitoring

10. **Enter dashboard loop** — The main window displays a live dashboard by reading worker status files. See `/spawn-bean` Step 4 for the full dashboard specification. The loop runs every ~30 seconds:
    - Read all `/tmp/agentic-worker-*.status` files and parse key-value pairs.
    - Render a dashboard table with progress bars (█/░), percentage (tasks_done/tasks_total), and color-coded status emoji.
    - Alert on `blocked` workers (🔴 with message and window switch shortcut) and `stale` workers (🟡, no status file update for 5+ minutes).
    - Cross-reference with `tmux list-windows` to detect closed windows (worker exited).
11. **Report completions** — As each worker finishes (status file shows `done` or window disappears), report in the dashboard.
12. **Merge, update index, and assign next bean** — When a worker completes:
    - Remove the worktree: `git worktree remove --force /tmp/agentic-worktree-BEAN-NNN`
    - Sync before merging: `git fetch origin && git pull origin test` — worktrees push to the remote, so the orchestrator's local `test` may be behind.
    - Merge the bean: run `/merge-bean NNN` from the main repo (merges feature branch into `test`).
    - Update `_index.md` on `test`: set the bean's status to `Done`. Commit and push. (The orchestrator is the sole writer of `_index.md`.)
    - Move the Trello card to Completed (same logic as sequential step 17b — check bean Notes for Trello source, find matching card in In_Progress list, move to Completed). Best-effort; do not block on failure.
    - Re-read the backlog for newly unblocked beans.
    - If an independent actionable bean exists, update `_index.md` to mark it `In Progress`, commit, create a new worktree, write its status file, and spawn a new worker window using the same launcher script pattern.
    - If no more beans, do not spawn.
    - To force-kill a stuck worker: `tmux kill-window -t "bean-NNN"`, then `git worktree remove --force /tmp/agentic-worktree-BEAN-NNN`

### Parallel Phase 5: Completion

13. **Check termination** — When all workers are done (status files show `done` or all windows closed) and no actionable beans remain, exit the dashboard loop.
14. **Final report** — Output: total beans processed, parallel vs sequential breakdown, all branch names created, remaining backlog status. End with: `⚠ Work is on the test branch. Run /deploy to promote to main.`
15. **Cleanup** — Remove status files: `rm -f /tmp/agentic-worker-*.status`. Run `git worktree prune` to clean up any stale worktree references.
16. **Sync local branches** — Worktrees pushed to the remote, so the original repo's refs are stale. Bring them up to date:
    - `git fetch origin && git pull origin test` (the orchestrator is already on `test`).
    - If local `main` is behind `origin/main`: `git branch -f main origin/main`.
    - This ensures the repo that launched `/long-run` has current refs when the user resumes work.

### Bean Assignment Rules

- Only assign beans with no unmet dependencies on other in-progress or pending beans.
- If fewer than N independent beans are available, spawn only as many workers as there are beans.
- Never assign the same bean to multiple workers.
- The main window orchestrates only — it does not process beans itself.

---

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| task_files | Markdown files | Task decompositions in each bean's `tasks/` directory |
| persona_outputs | Various files | Work products in `ai/outputs/<persona>/` |
| updated_beans | Markdown files | Bean status updated through lifecycle |
| updated_index | Markdown file | `_index.md` kept in sync with bean statuses |
| git_commits | Git commits | One commit per completed bean |
| progress_reports | Console text | Summary after each bean and at completion |

## Quality Criteria

- Each bean goes through the complete lifecycle: approved → in progress → decompose → execute → verify → close.
- No bean is skipped without explanation.
- Bean selection follows the documented heuristics consistently.
- All acceptance criteria are verified before marking a bean as Done.
- Tests and lint pass for every code bean before closing.
- Each bean is committed separately for clean git history.
- The loop terminates cleanly when the backlog is empty.
- In parallel mode: dependent beans are never assigned simultaneously.
- In parallel mode: the main window orchestrates only, never processes beans itself.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyBacklog` | No beans in `_index.md` | Report and exit cleanly |
| `NoActionableBeans` | All remaining beans are `Done`, `Deferred`, or blocked | Report status summary and exit |
| `TaskFailure` | A task cannot be completed | Report failure details, leave bean `In Progress`, stop loop |
| `TestFailure` | Tests or lint fail | Attempt to fix; if unresolvable, report and stop |
| `CommitFailure` | Git error during commit | Report error and stop for manual resolution |
| `MergeConflict` | Merge to test branch fails due to conflicts | Report conflicting files, abort merge, stop loop |
| `NotInTmux` | `--fast` used but `$TMUX` is not set | Instruct user to restart in tmux |
| `WorkerFailure` | A parallel worker fails on its bean | Report which worker/bean failed; other workers continue |

On error in sequential mode: the current bean stays `In Progress` and the loop stops. The user can inspect the state, fix the issue, and either re-run `/long-run` or manually complete the bean.

On error in parallel mode: a single worker failure does not stop other workers. The failed bean stays `In Progress`. The main window reports the failure and continues monitoring remaining workers.

## Dependencies

- Backlog index at `ai/beans/_index.md`
- Bean workflow at `ai/context/bean-workflow.md`
- Individual bean files at `ai/beans/BEAN-NNN-<slug>/bean.md`
- Git repository in a clean state (no uncommitted changes)
- Trello MCP server (optional — used for `/trello-load` sync and card completion; best-effort)
- `/trello-load` skill for sprint backlog import
