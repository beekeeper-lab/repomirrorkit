# Hook Pack: Git Push Feature

## Category
git

## Purpose

Pushes the current feature branch to origin with upstream tracking (`-u` flag). Validates branch naming conventions before pushing to prevent poorly named branches from reaching the remote.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `push-naming-check` | `pre-push` | Validate branch name matches project convention | Branch name matches naming pattern | Block push; show expected naming format |
| `push-upstream` | `post-commit` | Push feature branch to origin with `-u` flag for tracking | Push succeeds with upstream set | Warn; log push failure for manual retry |

## Configuration

- **Default mode:** enforcing
- **Timeout:** 30 seconds per hook
- **Customization:** Remote name and naming patterns configurable in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | advisory |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
