# Hook Pack: Git Merge to Test

## Category
git

## Purpose

Merges an approved pull request to the test integration branch. Runs pre-merge checks to ensure the feature branch is up to date and tests pass before merging. Uses `--no-ff` to preserve merge history.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `pr-approval-check` | `pre-merge` | Verify PR has at least one approval | PR status shows approved | Block merge; show approval requirements |
| `branch-up-to-date` | `pre-merge` | Check feature branch is rebased on latest test | No merge conflicts detected with test branch | Block merge; instruct to rebase/merge latest test |
| `merge-no-ff` | `post-approval` | Execute merge with `--no-ff` flag to preserve history | Merge commit created successfully | Block; report merge failure with conflict details |

## Configuration

- **Default mode:** enforcing
- **Timeout:** 60 seconds per hook
- **Customization:** Required approval count and target branch configurable in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | enforcing |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
