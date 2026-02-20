# Skill: Background Command Execution

## Description

Runs any slash command in a background tmux window. The user can continue working in their current window and switch to the background window when needed (e.g., for interactive approval prompts).

## Trigger

Invoked by the `/bg` slash command with a command name and optional arguments.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| command | String | Yes | The slash command to run (without leading `/`) |
| args | String | No | Arguments to pass to the command |

## Process

### Step 1: Parse Input

Extract the command name and any arguments from the user's input.

```
/bg deploy test        →  command="deploy", args="test"
/bg long-run --fast 3  →  command="long-run", args="--fast 3"
/bg backlog-refinement →  command="backlog-refinement", args=""
```

If no command name is provided, report usage and stop:
```
Usage: /bg <command> [args...]
Example: /bg deploy test
```

### Step 2: Validate Command Exists

Check that the command exists by looking for either:
- `.claude/commands/<command>.md`
- `.claude/commands/internal/<command>.md`
- `.claude/skills/<command>/SKILL.md`

If not found, report the error:
```
Unknown command: /<command>
Available commands: deploy, long-run, backlog-refinement, ...
```

### Step 3: Require tmux

Check that `$TMUX` is set. If not:
```
/bg requires tmux. Run /<command> directly instead.
```
Stop execution.

### Step 4: Spawn Background Window

Create a launcher script and spawn a new tmux window:

```bash
LAUNCHER=$(mktemp /tmp/foundry-bg-XXXXXX.sh)
cat > "$LAUNCHER" << 'SCRIPT_EOF'
#!/bin/bash
cd /home/gregg/Nextcloud/workspace/foundry
claude --dangerously-skip-permissions "/<command> <args>"
SCRIPT_EOF
chmod +x "$LAUNCHER"
tmux new-window -n "bg-<command>" "bash $LAUNCHER; rm -f $LAUNCHER"
```

Key details:
- **No `-p` flag** — positional arg gives visible TUI + auto-submit
- **No `--agent`** — the command itself specifies behavior
- **No worktrees** — commands operate on the current branch
- **Auto-cleanup** — launcher script is deleted after Claude exits
- **Auto-close** — tmux window closes when Claude exits

### Step 5: Report

```
Spawned /<command> in tmux window "bg-<command>".
Switch with `n (next) or `<N> (window number).
```

## Error Conditions

| Error | Resolution |
|-------|------------|
| No command provided | Show usage example |
| Unknown command | List available commands |
| Not in tmux | Suggest running the command directly |
| tmux new-window fails | Report the error from tmux |

## Key Rules

- **Simple wrapper.** No dashboards, status files, worktrees, or watchdogs.
- **Interactive commands work.** The user switches to the background window for prompts.
- **No collision guard.** Running `/bg deploy` twice creates two windows.
- **Window auto-closes.** When Claude exits, the window closes (established tmux pattern).
