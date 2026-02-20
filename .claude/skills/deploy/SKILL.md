# Skill: Deploy

## Description

Promotes a source branch into a target branch via a pull request. Creates the PR, runs tests, and merges if they pass. One approval, no extra prompts.

Two modes:
- `/deploy` — Promotes `test` → `main` (default). Full release with branch cleanup.
- `/deploy test` — Promotes current branch → `test`. Integration deploy for feature branches.

The three-tier deployment model is feature branch → `test` → `main`. The `main` branch is never pushed directly into `test`. If `/deploy test` is invoked while on `main`, the skill creates a temporary staging branch from the current `main` HEAD, resets the local `main` ref back to `origin/main`, and deploys the staging branch into `test` instead. This preserves the invariant that only feature/staging branches flow into `test`, and only `test` flows into `main`.

## Trigger

- Invoked by the `/deploy` slash command.
- Source branch must be ahead of target branch.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| target | String | No | Target branch: `main` (default) or `test` |
| tag | String | No | Version tag for the merge commit (e.g., `v1.2.0`). Only valid when target is `main`. |

## Branch Resolution

| Target | Source | Condition | Use Case |
|--------|--------|-----------|----------|
| `main` (default) | `test` | always | Release: promote integration branch to production |
| `test` | current branch | not on `main` | Integration: merge feature branch into test |
| `test` | auto-created `deploy/YYYY-MM-DD` | on `main`, commits ahead of `origin/main` | Staging: detach local-only main commits into a staging branch and deploy that into test |
| — | — | on `main`, nothing ahead of `origin/main` | Abort: nothing to deploy |

When target is `test` and you are not on `main`, the source is whatever branch you are on. This is typically a `bean/BEAN-NNN-<slug>` feature branch. When on `main`, a staging branch named `deploy/YYYY-MM-DD` is created (appending `-2`, `-3`, etc. on collision).

## Process

### Phase 1: Preparation

1. **Save current branch** — Record it so we can return at the end.
2. **Check for uncommitted changes** — Run `git status --porcelain`.
   - If clean: continue to step 3.
   - If dirty: show the list of modified/untracked files and prompt the user:
     - **Commit** — Stage all changes and commit with a message summarizing the changes (follow the repo's commit style). Then continue.
     - **Stash** — Run `git stash --include-untracked -m "deploy-auto-stash"`. Restore at the end.
     - **Abort** — Stop the deploy. The user should handle uncommitted changes manually.
3. **Determine source and target:**
   - If target is `main`: source = `test`. Checkout `test`.
   - If target is `test` AND **not on `main`**: source = the saved current branch. Stay on that branch.
   - If target is `test` AND **on `main`**:
     a. Check `git log origin/main..main --oneline`. If empty, report "Nothing to deploy — local main matches origin", restore stash, return. Exit.
     b. Compute staging name: `deploy/YYYY-MM-DD`. If that branch exists, append `-2`, `-3`, etc. until unique.
     c. `git checkout -b <staging>` — creates the staging branch from current HEAD (which has the local-only commits).
     d. `git branch -f main origin/main` — resets the local `main` ref back to match remote. This is safe because we are now on the staging branch, so no working-tree changes occur and no sandbox permission issues arise.
     e. source = the staging branch. Record that staging was used.
4. **Push source** — `git push origin <source>` to ensure remote is up to date.
5. **Verify ahead of target** — `git log <target>..<source> --oneline`. If empty, report "Nothing to deploy", restore stash, return to original branch, exit.

### Phase 1.5: Documentation Review

5a. **Identify what changed** — Review `git log <target>..<source> --oneline` and `git diff <target>..<source> --stat` to understand the scope of changes being deployed.

5b. **Check documentation checklist** — For each change, review the documentation checklist in `MEMORY.md` (section "Documentation Checklist") and verify that all applicable docs have been updated to reflect the changes. At minimum, always check:
   - `CLAUDE.md`, `README.md`, `ai/context/bean-workflow.md`, `ai/context/project.md`
   - All agent files in `.claude/agents/`
   - The relevant skill and command files in `.claude/skills/` and `.claude/commands/`
   - `CHANGELOG.md`
   - `docs/` for any project documentation

5c. **Search broadly** — Don't just grep for exact strings. Search for related concepts, synonyms, and soft references that may have become stale. For example, if the change modifies the team wave model, search for "wave", "BA", "Architect", "persona", "team", "decompose", etc.

5d. **Update stale docs** — If any documentation is stale, update it now on the source branch. Commit the documentation updates before proceeding.

5e. **Check if the checklist itself needs updating** — If the change introduces a new document or removes an existing one, update the Documentation Checklist in `MEMORY.md`.

5f. **Skip conditions** — This phase may be skipped if the deploy contains only documentation changes (no code or workflow changes) or if the user explicitly requests a fast deploy.

### Phase 2: Quality Gate

6. **Run tests** — `uv run pytest` on the source branch.
   - If any fail: report failures, restore stash, return to original branch. Stop.
   - If all pass: record the count.

7. **Run ruff** — `uv run ruff check foundry_app/`. Record result.

### Phase 3: Build Release Notes

8. **Identify beans** — Parse `git log <target>..<source> --oneline` for `BEAN-NNN:` messages. Cross-reference with `ai/beans/_index.md` for titles.

9. **Count branches to clean** (target=`main` only) — List all `bean/*` branches (local + remote). Count how many are merged into main.

### Phase 4: User Approval — ONE prompt

10. **Present summary and ask once:**
    ```
    ===================================================
    DEPLOY: <source> → <target> (via PR)
    ===================================================

    Beans: <list>
    Tests: N passed, 0 failed
    Ruff: clean / N violations

    Post-merge: N feature branches will be deleted
    (branch cleanup shown only for target=main)

    On "go": create PR, merge it, delete branches,
    restore working tree. No further prompts.
    ===================================================
    ```

11. **Single approval:**
    - Target `main`: go / go with tag / abort
    - Target `test`: go / abort

    **CRITICAL: This is the ONLY user prompt. Everything after "go" runs without stopping.**

### Phase 5: Execute (no further prompts)

12. **Create PR:**
    ```bash
    gh pr create --base <target> --head <source> \
      --title "Deploy: <date> — <bean list summary>" \
      --body "<release notes>"
    ```

13. **Merge PR:**
    ```bash
    gh pr merge <pr-number> --merge --subject "Deploy: <date> — <bean list>"
    ```
    Use `--merge` (not squash/rebase) to preserve history.

14. **Tag (optional, target=`main` only)** — If requested: `git tag <version> && git push origin --tags`.

15. **Delete local feature branches (target=`main` only)** — All `bean/*` branches merged into main: `git branch -d`. Stale/orphaned ones for Done beans: `git branch -D`.

16. **Delete remote feature branches (target=`main` only)** — Any `remotes/origin/bean/*`: `git push origin --delete`.

17. **Delete staging branch (if staging was used)** — After the PR merges, the staging branch is no longer needed:
    - Local: `git branch -D <staging>`.
    - Remote: `git push origin --delete <staging>`.

18. **Sync local target** — `git checkout <target> && git pull origin <target>`.

19. **Return to original branch** — If staging was used, return to `main` (since the staging branch no longer exists). Otherwise, `git checkout <original-branch>`.

20. **Restore stash** — If the user chose "Stash" in step 2: `git stash pop`. On conflict, prefer HEAD. (No action needed if the user chose "Commit".)

21. **Report success** — PR URL, merge commit, beans deployed, branches deleted (if applicable).

## Key Rules

- **One approval gate.** User says "go" once. Everything after is automatic.
- **Uncommitted changes prompt.** If the working tree is dirty, the user chooses: commit, stash, or abort. Nothing is silently discarded.
- **PR is created AND merged.** Not just created — the full cycle completes.
- **Branch cleanup only on main deploys.** Feature branches are cleaned up when promoting to main, not when merging to test.
- **If a command is blocked by sandbox:** print the exact command for the user to run manually, then continue with the rest.

## Error Conditions

| Error | Resolution |
|-------|------------|
| Nothing to deploy | Report and exit |
| Tests fail | Report failures, restore stash, return. Fix first. |
| PR create fails | Report error. Check `gh auth status`. |
| PR merge fails | Report error. Check branch protection / conflicts. |
| User aborts | Restore stash, return to original branch |
| On main with nothing to deploy | Local main matches origin/main — report "Nothing to deploy", exit |
| Staging branch reset fails | `git branch -f main origin/main` fails — abort deploy, leave staging branch for manual cleanup, report error |
| Command blocked | Print command for manual execution, continue |
