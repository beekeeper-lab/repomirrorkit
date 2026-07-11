# Task 1 — Config & CLI surface

**Files:** `harvester/config.py`, `harvester/cli.py`

- `HarvestConfig`: add `mirror: bool = False`, `keep_source: bool = False`,
  `cleanup: bool | None = None`; change `fail_on_fidelity` to `bool | None = None`.
- `__post_init__` resolution (before the BEAN-056 downgrade block):
  - mirror + `--no-llm` → `ConfigValidationError`
  - mirror + no `llm_api_key` → `ConfigValidationError` (actionable message)
  - mirror + `anthropic` package absent → `ConfigValidationError`
  - `cleanup`: None → `mirror`; `keep_source=True` forces False (wins)
  - `fail_on_fidelity`: None → `mirror`
- CLI: `--mirror`, `--keep-source`, `--cleanup` flags; `--fail-on-fidelity`
  default None; exit logic reads `config.fail_on_fidelity` (resolved), not the
  raw click param; echo cleanup outcome on success.

Owner: team-lead (Fable). Status: Done.
