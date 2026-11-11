# Task 4 — Tests

**Files:** new `tests/unit/test_cleanup.py`, additions to
`tests/unit/test_harvest_config.py`, `tests/unit/test_harvest_cli.py`,
`tests/unit/test_git_ops.py`, `tests/unit/test_state.py`,
`tests/integration/test_pipeline_e2e.py`

- Unit: every cleanup invariant (missing repo, symlink, no Stage-A state,
  missing `.git`, stray `.git` sweep); config mirror/key/flag matrix;
  CLI exit 3 without key; `get_head_sha`; state provenance/cleanup round-trip
  + back-compat.
- Integration (fixture, no LLM): `--cleanup` run → `repo/` gone, zero `.git`
  under out, beans + provenance present; `--resume` on cleaned dir re-clones
  and completes; mirror pipeline run with monkeypatched enrichment.

Owner: team-lead (Fable). Status: Done.
