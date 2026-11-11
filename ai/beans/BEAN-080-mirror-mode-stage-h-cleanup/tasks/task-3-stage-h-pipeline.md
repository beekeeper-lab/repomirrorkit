# Task 3 — Stage H cleanup module + pipeline wiring + resume fix

**Files:** new `harvester/cleanup.py`, `harvester/pipeline.py`,
`harvester/generator/assembler.py`, `harvester/generator/requirements_md.py`,
`harvester/reports/fidelity.py`

- `cleanup.py`: `CleanupError`, `CleanupResult`, `remove_source(output_dir, state)`.
  Invariants: target exactly `output_dir/"repo"`, not a symlink, resolves inside
  `output_dir`; Stage A must be recorded done in state; `.git` sanity check
  (warn-and-proceed when state confirms the clone); post-delete sweep removes
  any stray `.git` entries under `output_dir` (e.g. submodule gitlink files
  copied into `project-folder/`), erroring if one cannot be removed.
- `pipeline.py`: stage list gains "H" when `config.cleanup`; Stage H runs only
  after A–G all succeeded; records cleanup in state; `HarvestResult.cleanup_performed`.
  Resume: missing `repo/` → re-clone (with Stage A error handling) + HEAD-drift
  warning vs recorded provenance; provenance recorded on fresh clone and
  backfilled on resume.
- Provenance block rendered atop `REQUIREMENTS.md` (plumbed through
  `assemble_project_folder`), including whether the source tree is included.
- `fidelity.py`: `MIRROR_FIDELITY_THRESHOLDS` profile selected by `config.mirror`
  (values equal to defaults for now — raised via BEAN-076 amendment per
  SPEC-MIRROR-MODE.md M5.1).

Owner: team-lead (Fable). Status: Done.
