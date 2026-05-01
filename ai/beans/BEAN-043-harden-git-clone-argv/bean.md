# BEAN-043: Harden `git clone` Argv (Argument Terminator + URL Scheme Validation)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-043 |
| **Status** | In Progress |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 12:48 |
| **Completed** | — |
| **Duration** | — |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

The harvester invokes `git clone` via `subprocess.run` in `src/repo_mirror_kit/harvester/git_ops.py:122` with the argv list `["git", "clone", "--progress", url, str(workdir)]`. The list-form invocation correctly avoids shell-injection, but it is missing an argument-terminator (`--`) before the URL. A repository URL beginning with `-` (for example, `--upload-pack=…` or `--config=…`) can be parsed by `git clone` as an option flag rather than a URL, causing git to behave in attacker-influenced ways before the URL is even fetched. Additionally, the URL is passed straight through with no scheme validation: any string a user (or another component) hands to `clone_repository` becomes a `git clone` argument. The CLI accepts `--repo` with no validation at all (`harvester/cli.py:64-67`), while the GUI does call `validate_git_url` before submission — an inconsistent posture.

## Goal

`clone_repository` only attempts to clone URLs that pass a strict scheme allow-list (`https://`, `http://`, `ssh://`, `git@…:`, or absolute local paths), and the underlying `git clone` invocation includes an argument terminator so that no URL can be reinterpreted as a flag.

## Scope

### In Scope
- Add a private `_validate_clone_url(url: str)` helper in `git_ops.py` that raises a typed exception (e.g. `GitCloneError` with a clear message) for URLs that do not match the allow-list
- Call the validator at the top of `clone_repository` before any subprocess call
- Modify the `git clone` argv to insert `--` immediately before the URL: `["git", "clone", "--progress", "--", url, str(workdir)]`
- Add unit tests for the validator covering: valid https/ssh/scp/local-path inputs, rejected `-` / `--upload-pack=…` style inputs, rejected empty strings, rejected non-url-looking inputs
- Add a unit test asserting the argv list contains `--` immediately before the URL
- Verify the same helper is used (or referenced) anywhere else clone is invoked (e.g. `services/clone_service.py`)

### Out of Scope
- Wiring CLI-side URL validation (handled in BEAN-044)
- Network-level allowlist of hostnames or domains
- Mitigating malicious post-clone hooks (`.git/hooks`) — separate concern

## Acceptance Criteria

- [ ] `_validate_clone_url("--upload-pack=evil.sh")` raises `GitCloneError`
- [ ] `_validate_clone_url("https://github.com/user/repo.git")` returns without raising
- [ ] `_validate_clone_url("/abs/local/path")` returns without raising
- [ ] `clone_repository` invokes git with `--` immediately before the URL argument
- [ ] Existing `test_git_ops.py` tests still pass; new tests cover the validator and the argv shape
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Affected file: `src/repo_mirror_kit/harvester/git_ops.py:122`, plus any caller path
- Sibling: BEAN-044 (CLI URL validation parity) — both touch URL safety but at different boundaries; safe to ship in any order, but together they close the security gap
- Security Engineer should review the URL allow-list regex before merge

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 |      |       |          |           |            |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
