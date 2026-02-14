# /deploy Command

Promotes a source branch into a target branch via a pull request. Runs tests, creates the PR, merges it, and cleans up — all after a single user approval.

## Usage

```
/deploy [target] [--tag <version>]
```

- `target` -- Optional. Target branch: `main` (default) or `test`.
- `--tag <version>` -- Optional. Tag the merge commit with a version (e.g., `v1.2.0`). Only valid when target is `main`.

| Command | What It Does |
|---------|-------------|
| `/deploy` | `test` → `main` — Full release with branch cleanup |
| `/deploy test` | current branch → `test` — Integration merge for feature branches |
| `/deploy --tag v2.0.0` | `test` → `main` with version tag |

## Process

1. **Check for uncommitted changes** — if dirty, prompt: **Commit** (stage + commit), **Stash** (stash, restore at end), or **Abort**
2. **Determine source/target** — target `main`: source is `test`. Target `test`: source is current branch.
3. **Push source** to remote
4. **Run tests** (`uv run pytest`) and **ruff** (`uv run ruff check`) — stop if they fail
5. **Build release notes** from bean commits in `git log <target>..<source>`
6. **One approval prompt** — user says "go" (or "go with tag" for main), or "abort"
7. **Create PR** (`gh pr create --base <target> --head <source>`)
8. **Merge PR** (`gh pr merge --merge`) — preserves full commit history
9. **Tag** if requested (main only)
10. **Delete** merged feature branches, local + remote (main only)
11. **Sync target** locally, restore stash
12. **Report** — PR URL, merge commit, beans deployed, branches deleted

## Examples

```
/deploy              # Promote test → main
/deploy test         # Merge current feature branch → test
/deploy --tag v2.0.0 # Promote test → main with version tag
```

**Approval prompt (main):**
```
===================================================
DEPLOY: test → main (via PR)
===================================================

Beans: BEAN-029, BEAN-030, BEAN-033
Tests: 750 passed, 0 failed
Ruff: clean

Post-merge: 3 feature branches will be deleted

On "go": create PR, merge it, delete branches,
restore working tree. No further prompts.
===================================================
```

**Approval prompt (test):**
```
===================================================
DEPLOY: bean/BEAN-042-telemetry → test (via PR)
===================================================

Beans: BEAN-042
Tests: 565 passed, 0 failed
Ruff: clean

On "go": create PR, merge it,
restore working tree. No further prompts.
===================================================
```

## Error Handling

| Error | Resolution |
|-------|------------|
| Nothing to deploy | Report and exit |
| Tests fail | Report failures, stop. Fix on a bean branch first. |
| PR create fails | Check `gh auth status` and repo permissions |
| PR merge fails | Check branch protection rules or merge conflicts |
| Uncommitted changes | Prompted to commit, stash, or abort before proceeding |
| User aborts | Restore stash, return to original branch |
| Command blocked by sandbox | Prints exact command for manual execution, continues |
