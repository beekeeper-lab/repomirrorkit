# BEAN-044: CLI URL Validation Parity with GUI

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-044 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 12:52 |
| **Completed** | 2026-05-01 12:55 |
| **Duration** | 2h 4m |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

The PySide6 GUI calls `validate_git_url` on user input before submitting a clone (`src/repo_mirror_kit/views/main_window.py:115`, validator defined in `services/clone_service.py`). The CLI does not call this validator at all — `--repo` is accepted as-is and passed straight through to `HarvestConfig` and ultimately into `git_ops.clone_repository` (`harvester/cli.py:64-67`). This means the two entry points enforce different safety policies: a malformed or potentially dangerous URL is rejected if a user pastes it into the GUI but accepted if a user passes it on the command line. Beyond security, this hurts UX — bad URLs fail deeper in the pipeline with cryptic git errors instead of being flagged immediately at the boundary.

## Goal

Both the GUI and CLI enforce identical URL validation at the boundary, returning the same friendly error message for malformed input. `HarvestConfig` is the single point of truth: any caller that constructs a `HarvestConfig` with an invalid `repo` URL gets a `ConfigValidationError`.

## Scope

### In Scope
- Move `validate_git_url` from `services/clone_service.py` to a shared location accessible from both `services/` and `harvester/` (e.g. a new `src/repo_mirror_kit/url_validation.py`, or fold it into `harvester/config.py`)
- Call the validator inside `HarvestConfig` construction (or its `__post_init__`) so any invalid URL raises `ConfigValidationError`
- Confirm the GUI continues to use the same validator (no change in user-visible behavior on the GUI side)
- Update the CLI's existing `ConfigValidationError` handling (`cli.py:162-164`) so URL errors map cleanly to exit code 3 (already mapped — verify)
- Update or add tests so both entry points are covered

### Out of Scope
- Reconciling URL hardening at the `git clone` argv level (handled in BEAN-043)
- Adding network-level checks (DNS resolution, hostname allowlist)
- Restructuring the broader services/harvester relationship

## Acceptance Criteria

- [ ] A single canonical `validate_git_url` function is the only URL validator in the codebase (`grep -r "def validate_git_url" src/` returns exactly one match)
- [ ] Constructing `HarvestConfig(repo="--evil-flag", …)` raises `ConfigValidationError`
- [ ] Constructing `HarvestConfig(repo="https://github.com/x/y.git", …)` succeeds
- [ ] CLI invocation `requirements-harvester harvest --repo "--evil"` exits with code 3 and a clear error message
- [ ] GUI still rejects bad URLs with the same message as before
- [ ] Existing tests pass; new test in `test_harvest_config.py` covers the URL validation path
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Promote validator to public + wire into HarvestConfig | developer | — | Done |
| 2 | Verify parity + tests | tech-qa | 01 | Done |

> Skipped: BA, Architect (mechanical refactor + boundary-validation wiring).

### Verification (Tech-QA)

- ✅ `_validate_clone_url` (private, BEAN-043) promoted to `validate_clone_url` (public). Single canonical strict validator in `harvester/git_ops.py`.
- ✅ `services.clone_service.validate_git_url` is now a thin GUI-facing wrapper that calls `validate_clone_url` and converts `GitCloneError` → user-facing message string. GUI behavior preserved (still returns `None | str`).
- ✅ `HarvestConfig.__post_init__` calls `validate_clone_url` and converts `GitCloneError` → `ConfigValidationError`. Both CLI and direct constructors now reject malformed URLs at the boundary.
- ✅ Whitespace-rejection (was only in GUI) absorbed into the canonical validator so all callers get the same policy.
- ✅ New `TestHarvestConfigUrlValidation` covers accept (https/ssh/scp-like/abs path) and reject (`--upload-pack`, `ftp://`, no-scheme, spaces).
- ✅ All 4 pre-existing `test_clone_service.py` tests still pass without modification — the GUI wrapper preserves the `None | str` contract.
- ✅ `uv run pytest` — **1701 passed** (up from 1693).
- ✅ `uv run ruff check src/ tests/` — All checks passed.

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Sibling: BEAN-043 (clone argv hardening). Defense-in-depth: BEAN-044 catches bad URLs at the boundary; BEAN-043 protects the actual subprocess call.
- Either bean can ship first; doing both lands the full hardening posture.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Promote validator to public + wire into HarvestConfig | developer | — | — | — | — |
| 2 | Verify parity + tests | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 2 |
| **Total Duration** | 2h 4m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |