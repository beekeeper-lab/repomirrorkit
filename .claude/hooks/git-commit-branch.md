# Hook Pack: Git Commit Branch

## Category
git

## Purpose

Ensures commits go to a feature branch, never directly to protected branches (main, test, prod). Auto-creates a feature branch from the current branch name if the developer attempts to commit on a protected branch.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `branch-guard` | `pre-commit` | Check current branch against protected branch list | Current branch is not in `main`, `master`, `test`, `prod` | Block commit; prompt to create or switch to a feature branch |
| `branch-naming` | `pre-commit` | Validate feature branch name matches convention (`feature/`, `fix/`, `bean/`, etc.) | Branch name matches `^(feature|fix|bean|hotfix|chore)/[a-z0-9-]+$` | Warn; allow commit but log naming violation |

## Configuration

- **Default mode:** enforcing
- **Timeout:** 10 seconds per hook
- **Customization:** Protected branches and naming patterns can be overridden in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | enforcing |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
