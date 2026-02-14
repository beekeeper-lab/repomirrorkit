# /spawn-bean Command

Spawns one or more tmux workers, each running a Team Lead Claude Code agent that picks and executes a bean autonomously. Workers report progress via status files. The main window displays a live dashboard. Workers auto-submit their prompt and auto-close when done.

## Usage

```
/spawn-bean              # Spawn 1 window — team lead picks the best bean
/spawn-bean 16           # Spawn 1 window — team lead runs BEAN-016
/spawn-bean --count 3    # Spawn 3 windows — each team lead picks its own bean
/spawn-bean 16 17 18     # Spawn 3 windows — one per specified bean
/spawn-bean 16 17 18 --wide   # Same, but all in one window as tiled panes
/spawn-bean --count 4 --wide  # 4 auto-pick workers in a tiled grid
```

## Arguments

| Argument | Description |
|----------|-------------|
| `<bean-ids...>` | Optional. One or more bean IDs (e.g., `16`, `BEAN-016`). Each gets its own worker. |
| `--count N` or `-n N` | Spawn N workers. Each team lead auto-picks the highest-priority available bean. |
| `--wide` | Put all workers in a single window as tiled panes (for wide monitors). Without this flag, each worker gets its own window. |
| *(no args)* | Spawn 1 worker. Team lead auto-picks the best available bean. |

## Status File Protocol

Workers communicate progress back to the main window via status files in `/tmp/`. This enables the main window to display a live dashboard without polling the workers directly.

### File Location

Each worker writes to: `/tmp/agentic-worker-BEAN-NNN.status`

For single auto-pick workers (no bean ID, no `--count`), use: `/tmp/agentic-worker-auto-1.status` initially — the worker renames it to the real bean ID once it picks one. When using `--count N`, beans are pre-assigned so all status files use the real bean ID from the start.

### File Format

```
bean: BEAN-018
title: Library Indexer Service
tasks_total: 4
tasks_done: 2
current_task: 03-developer-implement
status: running
message:
worktree: /tmp/agentic-worktree-BEAN-018
updated: 2026-02-07T14:32:01
```

### Status Values

| Status | Meaning | Dashboard Color |
|--------|---------|-----------------|
| `starting` | Worker launched, claude initializing | ⚪ White/dim |
| `decomposing` | Breaking bean into tasks | 🔵 Blue |
| `running` | Executing tasks normally | 🟢 Green |
| `blocked` | Needs human input — see `message` field | 🔴 Red |
| `error` | Hit an unrecoverable error — see `message` | 🟠 Orange |
| `done` | Bean completed successfully | ✅ Done |

### When Workers Update the Status File

Workers must update their status file at each of these transitions:

1. **After picking a bean** — Set `status: decomposing`, fill in `bean`, `title`
2. **After decomposing into tasks** — Set `status: running`, fill in `tasks_total`, `tasks_done: 0`, `current_task`
3. **After completing each task** — Increment `tasks_done`, update `current_task` to the next task
4. **On blocker** — Set `status: blocked`, write explanation in `message`
5. **On error** — Set `status: error`, write error details in `message`
6. **On completion** — Set `status: done`, `tasks_done` equals `tasks_total`, clear `current_task`

Always update the `updated` timestamp when writing.

## Process

### Step 1: Determine what to spawn

- **Specific beans given** — Read `ai/beans/_index.md`. For each bean ID, verify it exists and has status `Approved` or `Deferred`. Resolve short IDs (e.g., `16` → `BEAN-016`). Extract the slug from the directory name.
- **`--count N`** — Read the index. Identify the top N beans by priority (High before Medium before Low) that have status `Approved`. Pre-assign all N beans — the orchestrator selects them upfront and creates isolated worktrees, eliminating race conditions.
- **No args** — Same as `--count 1`.

### Step 2: Create worktrees and launcher scripts

For **each** worker, create a git worktree for isolation, then create a launcher script. The worktree gives each worker its own independent working directory while sharing the same `.git` object store — no branch collisions, no file stomping.

```bash
# Variables — replace with actual values
BEAN_LABEL="BEAN-NNN"
BEAN_SLUG="BEAN-NNN-slug"
WINDOW_NAME="bean-NNN"
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREE_DIR="/tmp/agentic-worktree-${BEAN_LABEL}"
BRANCH_NAME="bean/${BEAN_SLUG}"
STATUS_FILE="/tmp/agentic-worker-${BEAN_LABEL}.status"
PROMPT="<prompt text from Step 3>"

# Clean stale worktree from a prior run if it exists
git worktree remove --force "$WORKTREE_DIR" 2>/dev/null

# Create feature branch + worktree
# If branch already exists (e.g., resuming), use it without -b
if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
  git worktree add "$WORKTREE_DIR" "$BRANCH_NAME"
else
  git worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR" main
fi

# Write initial status file so dashboard picks it up immediately
cat > "$STATUS_FILE" << EOF
bean: ${BEAN_LABEL}
title: (starting)
tasks_total: 0
tasks_done: 0
current_task:
status: starting
message:
worktree: ${WORKTREE_DIR}
updated: $(date -Iseconds)
EOF

# Create a temp launcher script — cd's to the worktree, NOT the main repo
LAUNCHER=$(mktemp /tmp/agentic-bean-XXXXXX.sh)
cat > "$LAUNCHER" << SCRIPT_EOF
#!/bin/bash
cd "$WORKTREE_DIR"
claude --dangerously-skip-permissions --agent team-lead \
  "$PROMPT"
SCRIPT_EOF
chmod +x "$LAUNCHER"
```

### Step 2a: Spawn workers (default — separate windows)

When `--wide` is **not** set, each worker gets its own tmux window:

```bash
tmux new-window -n "${WINDOW_NAME}" "bash $LAUNCHER; rm -f $LAUNCHER"
```

Each worker appears as a separate dot in the status bar. Switch between them with `Alt-N` or `` ` e ``.

### Step 2b: Spawn workers (`--wide` — tiled panes in one window)

When `--wide` is set, all workers share a single window as panes:

```bash
# First worker creates the window
tmux new-window -n "workers" "bash $LAUNCHER_1; rm -f $LAUNCHER_1"

# Additional workers split into panes within that window
tmux split-window -t "workers" "bash $LAUNCHER_2; rm -f $LAUNCHER_2"
tmux split-window -t "workers" "bash $LAUNCHER_3; rm -f $LAUNCHER_3"

# Auto-arrange into an even grid
tmux select-layout -t "workers" tiled
```

The `tiled` layout automatically arranges panes into a grid: 2 = side-by-side, 4 = 2x2, 6 = 2x3, etc. Each pane auto-closes when its claude exits. When the last pane closes, the window closes.

**Why this works (both modes):**
- **Auto-submit**: Passing the prompt as a positional argument to `claude` makes it start interactive mode and immediately process the prompt — no `send-keys` or sleep needed.
- **Auto-close**: When tmux runs a command (vs opening a bare shell), the window/pane automatically closes when the command exits.
- **Clean temp files**: Each launcher deletes itself after claude exits.

### Step 3: Craft the prompt

The prompt must include status file instructions so the worker reports progress.

**When a specific bean is given**, the prompt should be:

```
Pick BEAN-NNN (slug) using /pick-bean NNN, then execute the full bean lifecycle autonomously.

You are running in an ISOLATED GIT WORKTREE. Your feature branch (bean/BEAN-NNN-slug) is already checked out.
- Do NOT create or checkout branches — you are already on the correct feature branch.
- Do NOT run /merge-bean — the orchestrator handles merging after you finish.
- Do NOT checkout main or test — this will fail in a worktree if those branches are checked out elsewhere.

STATUS FILE PROTOCOL — You MUST update /tmp/agentic-worker-BEAN-NNN.status at every transition:
- Write the file using: cat > /tmp/agentic-worker-BEAN-NNN.status << 'SF_EOF'
  bean: BEAN-NNN
  title: <bean title>
  tasks_total: <N>
  tasks_done: <N>
  current_task: <current task filename or empty>
  status: <starting|decomposing|running|blocked|error|done>
  message: <empty or explanation for blocked/error>
  worktree: /tmp/agentic-worktree-BEAN-NNN
  updated: <ISO timestamp>
  SF_EOF
- Update after: picking the bean (decomposing), decomposing tasks (running, set tasks_total), completing each task (increment tasks_done), hitting a blocker (blocked + message), errors (error + message), and completion (done).
- CRITICAL: If you encounter a blocker requiring human input, set status to "blocked" with a clear message explaining what you need, then STOP and wait.

Bean lifecycle:
1. Decompose into tasks using /seed-tasks
2. Execute each task through the appropriate team persona
3. Use /close-loop after each task to verify acceptance criteria
4. Use /handoff between persona transitions
5. Run tests (uv run pytest) and lint (uv run ruff check) before closing
6. Commit all changes on the feature branch
7. Use /status-report to produce final summary
Work autonomously until the bean is Done. Do not ask for user input unless you encounter an unresolvable blocker.
```

**When auto-picking** (single worker, no bean ID specified — i.e., `/spawn-bean` with no args), the orchestrator does NOT create a worktree. The single worker runs in the main repo directory and handles its own branch:

```
You are a Team Lead. Read ai/beans/_index.md and pick the highest-priority bean with status Approved that is not owned by another agent. Use /pick-bean <id> to claim it, then execute the full bean lifecycle autonomously.

STATUS FILE PROTOCOL — You MUST update your status file at every transition:
- Your initial status file is at /tmp/agentic-worker-auto-1.status
- Once you pick a bean, RENAME the file: mv /tmp/agentic-worker-auto-1.status /tmp/agentic-worker-BEAN-NNN.status
- Then continue updating the renamed file.
- Write the file using: cat > /tmp/agentic-worker-BEAN-NNN.status << 'SF_EOF'
  bean: BEAN-NNN
  title: <bean title>
  tasks_total: <N>
  tasks_done: <N>
  current_task: <current task filename or empty>
  status: <starting|decomposing|running|blocked|error|done>
  message: <empty or explanation for blocked/error>
  updated: <ISO timestamp>
  SF_EOF
- Update after: picking the bean (decomposing), decomposing tasks (running, set tasks_total), completing each task (increment tasks_done), hitting a blocker (blocked + message), errors (error + message), and completion (done).
- CRITICAL: If you encounter a blocker requiring human input, set status to "blocked" with a clear message explaining what you need, then STOP and wait.

Bean lifecycle:
1. Decompose into tasks using /seed-tasks
2. Execute each task through the appropriate team persona
3. Use /close-loop after each task to verify acceptance criteria
4. Use /handoff between persona transitions
5. Run tests (uv run pytest) and lint (uv run ruff check) before closing
6. Commit all changes on the feature branch
7. Use /merge-bean to merge into test
8. Use /status-report to produce final summary
Work autonomously until the bean is Done. Do not ask for user input unless you encounter an unresolvable blocker.
```

**When using `--count N`** (multiple workers), each bean is pre-assigned by the orchestrator with its own worktree. Use the **specific bean prompt** above — every worker knows its bean ID and runs in its isolated worktree.

### Step 4: Dashboard — monitor workers from the main window

After all workers are spawned, the main window enters a **dashboard monitoring loop**. This runs in the orchestrator's Claude session (the one that ran `/spawn-bean`).

**Dashboard loop:**

1. Read all `/tmp/agentic-worker-*.status` files.
2. For each file, parse the key-value pairs.
3. Compute progress percentage: `tasks_done / tasks_total * 100` (show 0% if `tasks_total` is 0).
4. Check for stale workers: if `updated` timestamp is older than 5 minutes and status is `running`, mark as `🟡 Stale` in the display.
5. Render the dashboard table (see format below).
6. If any worker has `status: blocked`, display an alert with the message and which window to switch to.
7. If all workers show `status: done` or their status files are gone (window closed), report completion and exit the loop.
8. Wait ~30 seconds, then repeat from step 1.

**Dashboard display format:**

```
╔══════════════════════════════════════════════════════════════════╗
║  Bean Workers — 3 active                          14:32:01     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  BEAN-018  Library Indexer Service     ████████░░  50% (2/4)    ║
║  🟢 Running — 03-developer-implement                           ║
║                                                                 ║
║  BEAN-019  Wizard Project Identity     ██████████░ 75% (3/4)    ║
║  🟢 Running — 04-tech-qa-tests                                 ║
║                                                                 ║
║  BEAN-020  Wizard Persona Selection    ███░░░░░░░  25% (1/4)    ║
║  🔴 FEEDBACK NEEDED — Need clarification on persona filter UX   ║
║     → Switch to worker: Alt-3                                   ║
║                                                                 ║
╚══════════════════════════════════════════════════════════════════╝

⚠  1 worker needs attention — see 🔴 above
```

**How to render this:** Use simple `print()` output with Unicode box-drawing characters. The progress bar uses `█` (filled) and `░` (empty) with 10 segments. Color indicators use emoji since they render in all terminals.

**Alerting on blocked workers:**

When a worker has `status: blocked`:
- The dashboard highlights that row with 🔴 and shows the `message` text
- Below the table, print a prominent alert: `⚠  N worker(s) need attention`
- Include the window switch shortcut so the user can jump there immediately

**Worker completion — orchestrator merge:**

When a worker's status changes to `done` (or its window/pane closes):

1. **Remove the worktree**: `git worktree remove --force /tmp/agentic-worktree-BEAN-NNN`
2. **Merge the bean**: Run `/merge-bean NNN` from the main repo to merge the feature branch into `test`.
3. **Spawn replacement**: If actionable beans remain in the backlog, create a new worktree + launcher for the next bean and spawn a replacement worker.

This ensures merges happen sequentially from the main repo (avoiding the worktree limitation where `test` can't be checked out from a worktree if it's in use elsewhere).

**Dashboard exit conditions:**
- All status files show `done` and all merges complete → print completion summary, clean up status files, exit
- All worker windows/panes have closed → print completion summary, clean up any remaining status files, exit
- User interrupts → exit cleanly (status files remain for inspection)

### Step 5: Cleanup

Workers clean up automatically:
- When claude exits (bean done or error), the window/pane closes automatically.
- The temp launcher script deletes itself after use.
- Status files persist in `/tmp/` until the dashboard exits and cleans them up, or until the OS cleans `/tmp/`.
- The dashboard cleans up status files when all workers complete: `rm -f /tmp/agentic-worker-*.status`
- **Worktree cleanup**: The orchestrator removes each worktree after merging (see Step 4). As a final safety net, run `git worktree prune` after all workers complete to clean up any stale worktree references.
- To force-kill a stuck worker:
  - **Windows mode**: `tmux kill-window -t "bean-NNN"`
  - **Wide mode**: switch to the "workers" window, select the pane, and `` ` x `` to kill it
  - After killing, also remove the worktree: `git worktree remove --force /tmp/agentic-worktree-BEAN-NNN`

## Important Notes

- Each spawned Claude runs with `--dangerously-skip-permissions` and `--agent team-lead`
- **Windows mode** (default): each worker is a separate window (dot in status bar). Navigate with `Alt-N` or `` ` e ``
- **Wide mode** (`--wide`): all workers share one window as tiled panes — ideal for large monitors where you can see all workers at once
- **Git worktrees** provide isolation: each worker gets its own working directory at `/tmp/agentic-worktree-BEAN-NNN/`. No branch collisions, no file stomping between workers.
- **Pre-assignment** eliminates race conditions: when using `--count N`, the orchestrator selects all beans upfront and creates worktrees before spawning. No stagger delay needed.
- **Orchestrator merges**: Workers do NOT run `/merge-bean`. The orchestrator handles merging sequentially after each worker completes, since worktrees cannot checkout `test` if it's checked out elsewhere.
- **`uv` in worktrees**: Each worktree auto-creates its own `.venv` on first `uv run` — works seamlessly.
- Child agents work fully autonomously — no user input needed for normal flow
- Workers auto-close when done — no manual cleanup needed (both windows and panes)
- **Status files** in `/tmp/agentic-worker-*.status` are the communication channel — the dashboard reads these, workers write them
- The dashboard refreshes every ~30 seconds and alerts on blocked/stale workers
- To check all bean status from this (coordinator) window: `/bean-status`
- Max recommended parallel workers: 3-5 (depends on system resources and API rate limits)
