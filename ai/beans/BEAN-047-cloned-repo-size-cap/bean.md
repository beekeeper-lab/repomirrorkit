# BEAN-047: Add Total-Size Cap on Cloned Repository

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-047 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester accepts arbitrary Git repositories, including remote URLs, and clones them in full. The existing `--max-file-bytes` flag (`src/repo_mirror_kit/harvester/cli.py:91`) bounds *per-file* read size during inventory, but does nothing to bound the **total** size of the working copy. A malicious or pathological repository — many small files, a deep history with large packs, generated artifacts, vendored dependencies — can fill the disk before inventory even begins. This is a denial-of-service vector against shared CI runners and developer machines, and a poor failure mode for honest-but-large repositories that the user did not realize were huge.

## Goal

The harvester refuses to process a clone whose total on-disk size exceeds a configurable cap. The cap is enforced as soon as possible after clone (Stage A) so that bounded resources are consumed before the (much more expensive) analysis stages run. Default cap is generous enough for normal projects (suggest 500 MiB) but small enough to prevent runaway behavior; the cap is overridable on the CLI.

## Scope

### In Scope
- Add `--max-total-bytes` flag to the CLI with a sensible default (proposed: 500 MiB)
- Add `max_total_bytes` field to `HarvestConfig`
- Implement a `_compute_total_size(workdir: Path) -> int` helper in `git_ops.py` that walks the clone and sums file sizes (excluding `.git` if appropriate — decision recorded in implementation)
- After clone in Stage A, compute total size; if it exceeds the cap, raise `GitCloneError("Repository exceeds size cap of N bytes; got M bytes")` and clean up the partial clone
- Add a unit test with a fixture directory exceeding a small cap; assert the error is raised
- Update `--help` text and README to mention the new flag

### Out of Scope
- Streaming/abort-during-clone (would require parsing git progress output) — defer
- Per-extension or per-path size caps
- Clone depth limits (`--depth=1`) — separate optimization

## Acceptance Criteria

- [ ] `requirements-harvester harvest --help` shows `--max-total-bytes` with its default
- [ ] `HarvestConfig.max_total_bytes` defaults to the documented value
- [ ] A clone whose total size exceeds the cap raises `GitCloneError` and exits with a non-zero code
- [ ] The partial clone directory is removed on size-cap failure (no half-cloned repos left behind)
- [ ] Unit test in `test_git_ops.py` covers the size-cap failure path
- [ ] Honest-but-large repository test: cloning a small fixture under the cap succeeds with no behavior change
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Sibling bean: BEAN-043 (clone argv hardening). Both are clone-stage hardening; can be done in either order
- The `_compute_total_size` walk should follow symlinks safely (avoid loops) and skip `.git` to focus the cap on the working copy that drives inventory

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
