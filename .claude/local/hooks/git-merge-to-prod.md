# Hook Pack: Git Merge to Prod

## Category
git

## Purpose

Merges the test branch to prod/main after approval, with safety gates requiring CI to be green and a minimum approval count. This is the final gate before production deployment.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `ci-green-check` | `pre-merge` | Verify all CI checks on test branch are passing | All required status checks show success | Block merge; list failing checks |
| `approval-count` | `pre-merge` | Verify minimum number of approvals met | At least N approvals (default: 2) | Block merge; show current vs required approval count |
| `changelog-check` | `pre-merge` | Verify CHANGELOG.md has been updated for this release | Changelog has unreleased or version entry matching | Warn; remind to update changelog |
| `prod-merge` | `post-approval` | Execute merge from test to main/prod with `--no-ff` | Merge commit created on production branch | Block; report merge failure details |

## Configuration

- **Default mode:** enforcing
- **Timeout:** 60 seconds per hook
- **Customization:** Required approval count, CI check names, and production branch name configurable in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | enforcing |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
