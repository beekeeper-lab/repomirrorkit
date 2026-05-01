# BEAN-045: Drop `--llm-api-key` CLI Flag and Add Helpful Missing-Key Guidance

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-045 |
| **Status** | In Progress |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 12:56 |
| **Completed** | — |
| **Duration** | — |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

The CLI exposes `--llm-api-key` as a command-line option (`src/repo_mirror_kit/harvester/cli.py:121-125`). Accepting an API key on the command line is a long-standing security anti-pattern: the key ends up in the user's shell history, in `ps`-visible argv on Linux until the process exits, and potentially in CI logs that record full command lines. The flag also already coexists with a perfectly good `ANTHROPIC_API_KEY` environment variable path (Click's `envvar=` is wired). Removing the flag eliminates the leakage path with no functional cost.

A separate but related UX gap: when a user runs the harvester with `--llm-enabled` but no API key set, the resulting failure should clearly explain (a) where to obtain a key (`https://console.anthropic.com/settings/keys`), (b) which env var to set, and (c) the exact shell line to set it. Today the failure mode is opaque.

## Goal

The CLI accepts the Anthropic API key via the `ANTHROPIC_API_KEY` environment variable only. When LLM enrichment is requested but no key is found, the CLI emits a single clear, actionable error message that tells the user how to fix the problem.

## Scope

### In Scope
- Remove the `--llm-api-key` Click option from `harvester/cli.py`
- Keep the `envvar="ANTHROPIC_API_KEY"` resolution path
- Implement a `_resolve_api_key()` helper (or equivalent) that reads the env var and, when missing while `--llm-enabled` is set, raises a `ConfigValidationError` whose message includes:
  - "ANTHROPIC_API_KEY is not set"
  - A pointer to `https://console.anthropic.com/settings/keys` to obtain a key
  - The exact `export ANTHROPIC_API_KEY=…` shell line
  - A note that the key is never logged
- Update tests in `test_harvest_cli.py` / `test_harvest_config.py` to cover the new error path
- Update `--help` output and any README text that referenced the flag

### Out of Scope
- Flipping the `--llm-enabled` default (handled in BEAN-056)
- Adding an interactive credentials prompt (out of scope for a CLI tool used in CI)
- Storing keys via OS keyring or secret manager

## Acceptance Criteria

- [ ] `requirements-harvester harvest --help` does not list `--llm-api-key`
- [ ] Running `requirements-harvester harvest --repo … --llm-enabled` with `ANTHROPIC_API_KEY` unset prints a helpful, multi-line error pointing to the console URL and the exact `export` command, then exits with code 3
- [ ] Running with `ANTHROPIC_API_KEY` set succeeds (smoke test against a small repo)
- [ ] No reference to `--llm-api-key` remains in `src/`, `tests/`, or `README.md` (`grep -r "llm-api-key" .` empty outside this bean)
- [ ] The API key string is never logged at any log level (verify by running with `--log-level debug` and grepping output)
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Security / hardening" (2026-05-01)
- Sibling/successor: BEAN-056 (LLM default-on). The helpful-missing-key error landed in this bean becomes the common path once BEAN-056 flips the default — the UX work belongs here so BEAN-056 inherits it for free.
- Security Engineer review on the redaction check (no key in logs) before merge

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
