# BEAN-043 Task 01: Add URL validator + argv terminator

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Status** | Done |
| **Started** | 2026-05-01 12:49 |
| **Completed** | 2026-05-01 12:51 |
| **Duration** | 2m |
| **Depends On** | — |

## Goal

Add `_validate_clone_url(url)` to `git_ops.py` enforcing a strict URL scheme allow-list (`https://`, `http://`, `ssh://`, `git@…:`, absolute local paths). Call it at the top of `clone_repository`. Add `--` immediately before the URL in the `git clone` argv so a malicious URL starting with `-` cannot be misparsed as a flag. Add unit tests for both.

## Inputs

- `src/repo_mirror_kit/harvester/git_ops.py:112-145` (`_run_clone`)
- `tests/unit/test_git_ops.py` (existing test patterns)

## Acceptance Criteria

- [ ] `_validate_clone_url("--upload-pack=evil")` raises `GitCloneError`
- [ ] `_validate_clone_url("https://github.com/x/y.git")` returns
- [ ] `_validate_clone_url("ssh://git@host:repo")` returns
- [ ] `_validate_clone_url("git@github.com:x/y.git")` returns
- [ ] `_validate_clone_url("/abs/local/path")` returns
- [ ] `_validate_clone_url("")` raises
- [ ] `clone_repository` invokes git with `["git", "clone", "--progress", "--", url, str(workdir)]`
- [ ] New tests added in `test_git_ops.py`; full pytest + ruff clean

## Definition of Done

- All AC met; changes committed on the feature branch.
