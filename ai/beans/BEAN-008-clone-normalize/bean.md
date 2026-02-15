# BEAN-008: Clone & Normalize (Stage A)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-008 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | <1 day |
| **Owner** | Developer |
| **Category** | App |

## Problem Statement

The harvester pipeline's first stage must clone the target repository into a temporary working directory, optionally check out a specific ref (branch/tag/SHA), and normalize the working copy for analysis. The existing `clone_service.py` handles basic cloning to `./projects/`, but the harvester needs cloning to a temp directory, ref checkout, line ending normalization, and safe symlink handling.

## Goal

Implement Stage A of the harvester pipeline: a `git_ops.py` module that clones a repository to a temp workdir, checks out a specified ref, normalizes line endings, and safely resolves symlinks (never following symlinks outside the repo).

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/git_ops.py`
- Clone repository to a temporary working directory (not `./projects/`)
- Support `--ref` to checkout a specific branch, tag, or SHA after clone
- Default to the repo's default branch if no ref specified
- Normalize line endings (CRLF → LF) for consistent analysis
- Resolve symlinks safely: do not follow symlinks that point outside the repo
- Verify `git` is available on PATH (reuse pattern from existing `clone_service.py`)
- Emit structured log events for clone progress
- Write checkpoint to state: `{ stage: "A", status: "done" }`
- Unit tests with mocked subprocess for clone, ref checkout, and normalization

### Out of Scope
- Rewriting the existing `clone_service.py` (BEAN-002's service stays for GUI clone to `./projects/`)
- Authentication for private repos (SSH keys, tokens)
- Shallow cloning or partial cloning optimizations
- Cleanup of temp directories (handled by orchestrator or OS)

## Acceptance Criteria

- [x] `git_ops.clone_repository(url, ref, workdir)` clones to the specified temp directory
- [x] If `--ref` is provided, the specified ref is checked out after clone
- [x] If `--ref` is not provided, the default branch is used
- [x] Invalid ref produces a clear error (not a cryptic git message)
- [x] Line endings are normalized to LF in the working copy
- [x] Symlinks pointing outside the repo are identified and skipped (not followed)
- [x] Missing `git` on PATH produces a clear error message
- [x] Clone progress is logged via structlog
- [x] State checkpoint is written after successful Stage A completion
- [x] Unit tests cover: successful clone, ref checkout, missing git, invalid ref, symlink safety
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement git_ops.py | Developer | BEAN-004, BEAN-006 | Done |
| 2 | Unit tests for git_ops | Developer | Task 1 | Done |
| 3 | Tech QA verification | Tech QA | Task 1, 2 | Done |

## Notes

- Depends on BEAN-004 (Harvester Package Setup) and BEAN-006 (State Management).
- The existing `clone_service.py` from BEAN-002 handles GUI-triggered cloning to `./projects/`. This module is separate — it handles harvester-specific cloning to a temp directory with additional normalization.
- Reference: Spec section 6, Stage A (Clone & normalize).
- Consider using `tempfile.mkdtemp()` for the working directory.
- The symlink safety check should use `os.path.realpath()` to resolve and verify the target is within the repo root.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Implement git_ops.py | Developer | — | — | — |
| 2 | Unit tests | Developer | — | — | — |
| 3 | Tech QA | Tech QA | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 3 |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
