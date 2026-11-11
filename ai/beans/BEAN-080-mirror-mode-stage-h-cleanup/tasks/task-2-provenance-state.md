# Task 2 — Provenance capture + state records

**Files:** `harvester/git_ops.py`, `harvester/state.py`

- `CloneResult.head_sha: str | None = None`; new `get_head_sha(workdir)` via
  `git rev-parse HEAD`; populated by `clone_repository` after checkout.
- `PipelineState`: add `provenance: dict | None` and `cleanup: dict | None`;
  tolerant (back-compat) `from_dict`; included in `to_dict`.
- `StateManager`: `record_provenance()` (stamps `harvested_at` if absent),
  `get_provenance()`, `record_cleanup()`.

Owner: team-lead (Fable). Status: Done.
