# /bg Command

Runs any slash command in a background tmux window so you can keep working in your current window.

## Usage

```
/bg <command> [args...]
```

| Command | What It Does |
|---------|-------------|
| `/bg deploy` | Run `/deploy` in background window `bg-deploy` |
| `/bg deploy test` | Run `/deploy test` in background window `bg-deploy` |
| `/bg long-run --fast 3` | Run `/long-run --fast 3` in background window `bg-long-run` |
| `/bg backlog-refinement "ideas"` | Run `/backlog-refinement "ideas"` in background window `bg-backlog-refinement` |

## Process

1. Parse command name and arguments from input
2. Validate the command exists in `.claude/commands/` or `.claude/skills/`
3. Require `$TMUX` — error if not in a tmux session
4. Create a launcher script and spawn a new tmux window running Claude with the command
5. Report the window name and how to switch to it

## Switching to Background Windows

- `` `n `` — next window
- `` `p `` — previous window
- `` `<N> `` — switch to window number N

## Notes

- The background window closes automatically when the command finishes
- Interactive commands (like `/deploy`) work fine — switch to the window when it needs input
- Running `/bg <command>` twice creates two windows — no collision guard
- No worktrees, dashboards, or status files — just a simple tmux wrapper

## Error Handling

| Error | Resolution |
|-------|------------|
| Not in tmux | Report error, suggest running the command directly |
| Unknown command | Report which command was not found |
| Missing command name | Show usage |
