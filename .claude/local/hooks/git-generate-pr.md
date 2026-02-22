# Hook Pack: Git Generate PR

## Category
git

## Purpose

Creates a pull request from the current feature branch to the test branch using `gh pr create`. Generates a structured PR body from commit history and task metadata. Requires the GitHub CLI (`gh`) to be installed and authenticated.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `gh-cli-check` | `pre-pr-create` | Verify `gh` CLI is installed and authenticated | `gh auth status` returns success | Block PR creation; instruct to install/authenticate gh |
| `pr-create` | `post-task-complete` | Create PR from feature branch to test using `gh pr create` | PR created successfully with URL returned | Warn; log failure and provide manual command |
| `pr-template` | `pre-pr-create` | Validate PR has summary, test plan, and linked task ID | Required sections present in PR body | Block PR; show template with missing sections |

## Configuration

- **Default mode:** advisory
- **Timeout:** 30 seconds per hook
- **Customization:** Target branch, PR template, and required sections configurable in `.foundry/hooks.yml`

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | advisory |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |
