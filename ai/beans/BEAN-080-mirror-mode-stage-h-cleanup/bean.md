# BEAN-080: `--mirror` Mode + Stage H Cleanup (Delete Source & Git History)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-080 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-07-11 |
| **Started** | 2026-07-11 10:48 |
| **Completed** | 2026-07-11 11:50 |
| **Duration** | ~62m |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

The harvester's output directory keeps the full cloned working copy (`<out>/repo/`, including its `.git/`) after the run. For the mirror-mode goal — a self-contained requirements package that an agent rebuilds *from the output alone* — the original source is not only unnecessary, it is a liability: an agent operating in the output dir could accidentally commit/push mass deletions via the leftover clone remote, the source invites transliteration instead of reimplementation, and there is no enforcement of "output alone is sufficient." Additionally, a run without `ANTHROPIC_API_KEY` silently downgrades to structural-only output (`config.py:107-126`), which can never reach mirror-grade fidelity, and no provenance (repo URL + commit SHA) is recorded, so `source_refs` lose meaning once the source is gone.

Full design: `SPEC-MIRROR-MODE.md` Phase 1 (M1.1–M1.5), decisions D3/D4.

## Goal

`requirements-harvester harvest --repo <url> --mirror` completes with an output directory containing **no `repo/` and no `.git` anywhere**, provenance (URL, ref, HEAD SHA, timestamp) recorded in `state.json` and `REQUIREMENTS.md`, and fails fast (exit 3) when `ANTHROPIC_API_KEY` is missing. Default (non-mirror) behavior is unchanged.

## Scope

### In Scope
- `HarvestConfig.mirror` / `keep_source` / `cleanup` fields + `--mirror`, `--keep-source`, `--cleanup` CLI flags. Resolution: mirror → cleanup on; `--cleanup` forces on; `--keep-source` forces off and always wins.
- Mirror semantics: missing key or missing `anthropic` package → hard error exit 3 with actionable message; forces `llm_enabled=True`; flips `--fail-on-fidelity` default to true; selects mirror fidelity threshold profile (minimal profile plumb-through — full thresholds are BEAN-076 amendment territory).
- Provenance: `CloneResult.head_sha` via `git rev-parse HEAD` (`git_ops.py`); persist `{repo_url, ref, head_sha, harvested_at}` to `state.json`; provenance block atop `REQUIREMENTS.md` ("source refs refer to `<url>` @ `<sha>`; source tree not included").
- New `harvester/cleanup.py` Stage H, appended to stage list (`pipeline.py:84`) and `StateManager`. Runs **only when Stages A–G all succeeded**. Safety invariants (all mandatory): target is exactly `output_dir / "repo"`, resolved, inside `output_dir`, not a symlink; `state.json` must record Stage A cloned it (never delete a `repo/` we didn't create); sanity-check `.git/` present (warn if state confirms clone but `.git` absent); post-delete walk asserts **zero `.git` remains anywhere** under `output_dir`, failing loudly otherwise. Record `{removed, files_removed, bytes_freed, completed_at}` in state; structlog summary.
- Resume fix: `--resume` with `repo/` missing forces re-clone (fix at `pipeline.py:256-265`); warn on HEAD-SHA drift vs recorded provenance when no `--ref` pins the checkout.

### Out of Scope
- Verbatim rule capture / template changes (BEAN-081, BEAN-082).
- Sensitive-findings surfacing (BEAN-083).
- Full mirror fidelity thresholds (amendment to BEAN-076, see spec M5.1).
- Flipping cleanup default-on for non-mirror runs.

## Acceptance Criteria

- [x] Mirror run on the `python-flask` fixture: exit 0/2, `repo/` absent, zero `.git` under `<out>/`, beans present, provenance in `state.json` and `REQUIREMENTS.md`. *(integration test + live CLI run 2026-07-11)*
- [x] `--mirror` without `ANTHROPIC_API_KEY` exits 3 with an actionable message; default `harvest` (no `--mirror`) behavior is byte-for-byte unchanged. *(live probe: exit 3; full pre-existing suite green)*
- [x] `--keep-source` preserves `repo/`; `--cleanup` without `--mirror` removes it; `--keep-source` wins over both. *(unit + live probes)*
- [x] Cleanup never runs when any stage A–G failed (working copy survives for debugging). *(Stage H reached only after G succeeds; early returns skip it)*
- [x] Every cleanup safety invariant has a unit test (wrong dir, symlink target, no state record, missing `.git`, failure-path skip). *(tests/unit/test_cleanup.py)*
- [x] `--resume` on a cleaned output dir re-clones and completes; drift warning fires when re-cloned HEAD differs from recorded SHA. *(integration test + live probe)*
- [x] All tests pass *(1874 passed)*
- [x] Lint clean *(ruff check + format, mypy src/ strict clean, tests at pre-existing baseline)*

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Approved by operator (Gregg) 2026-07-11 — "Follow your recommendation and do what is next" after the recommendation to approve BEAN-080 and implement it directly.
- Spec: `SPEC-MIRROR-MODE.md` Phase 1; review surface: `artifacts/html/implementation-plans/mirror-mode-spec.html`.
- Files touched: `cli.py`, `config.py`, `pipeline.py`, `state.py`, `git_ops.py`, `generator/requirements_md.py`, new `cleanup.py`, tests.
- Precedent for deletion: the failed-clone size-cap `shutil.rmtree` at `git_ops.py:182` — Stage H is the success-path counterpart with far stricter guards.
- Ship first: this bean alone delivers the operator's core ask end-to-end and is flag-gated (rollback = don't pass the flags).

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Config & CLI surface | team-lead | — | — | — |
| 2 | Provenance + state records | team-lead | — | — | — |
| 3 | Stage H module + pipeline + resume | team-lead | — | — | — |
| 4 | Tests | team-lead | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 4 |
| **Total Duration** | ~62m (wall clock) |
| **Total Tokens In** | (not tracked) |
| **Total Tokens Out** | (not tracked) |
