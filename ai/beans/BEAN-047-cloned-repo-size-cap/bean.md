# BEAN-047: Add Total-Size Cap on Cloned Repository

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-047 |
| **Status** | Done |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 13:01 |
| **Completed** | 2026-05-01 13:03 |
| **Duration** | 2h 12m |
| **Owner** | team-lead |
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
| 1 | Add --max-total-bytes + post-clone size check | developer | — | Done |
| 2 | Verify cap behavior + tests | tech-qa | 01 | Done |

> Skipped: BA, Architect (small additive feature, well-defined surface).

### Verification (Tech-QA)

- ✅ `--max-total-bytes` CLI flag added (default 500 MiB = 524,288,000 bytes); shown in `--help`.
- ✅ `HarvestConfig.max_total_bytes` field with `DEFAULT_MAX_TOTAL_BYTES` constant; validated as positive in `__post_init__`.
- ✅ `_compute_total_size(workdir)` walks the working copy summing regular-file sizes, skips `.git`, skips symlinks.
- ✅ `clone_repository` accepts `max_total_bytes` keyword; after clone, computes total and raises `GitCloneError("...exceeds cap...")` if over the limit. Partial clone is removed via `shutil.rmtree` so no half-state on disk.
- ✅ `pipeline.HarvestPipeline._run_stage_a` passes `config.max_total_bytes` through.
- ✅ 4 new tests in `TestSizeCap`: `_compute_total_size` excludes `.git`, skips symlinks; `clone_repository` aborts + cleans up when over cap; succeeds when under cap.
- ✅ Suite: 1717 passed (up from 1713). Ruff clean.

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Sibling bean: BEAN-043 (clone argv hardening). Both are clone-stage hardening; can be done in either order
- The `_compute_total_size` walk should follow symlinks safely (avoid loops) and skip `.git` to focus the cap on the working copy that drives inventory

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Add --max-total-bytes + post-clone size check | developer | — | — | — | — |
| 2 | Verify cap behavior + tests | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 2 |
| **Total Duration** | 2h 12m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |