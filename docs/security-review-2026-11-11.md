# Security review — recreation pipeline additions (2026-11-11)

Scope: code added or changed in this program of work. Reviewed by the implementing agent against the project's cross-cutting safety rules (no secrets in code/logs, validate boundaries, least privilege, dependency discipline). This is a self-review, not an independent audit.

## Findings and dispositions

| # | Area | Finding | Disposition |
|---|------|---------|-------------|
| 1 | Parity runner (`parity/server.py`) | The app under test (LLM-generated, **untrusted**) inherited the operator's full environment, including API keys. Found when a test dumped the environment. | **Fixed**: apps see only `SAFE_ENV_KEYS` plus explicit `--env`; `inherit_env=True` is opt-in; regression test asserts no `*_API_KEY`/`*_TOKEN`/`*_SECRET` names reach the app. Earlier eval runs in this session predate the fix (apps were localhost-only and short-lived). |
| 2 | Parity runner | The rebuilt app still runs as the operator's user with network and filesystem access. | **Residual / documented**: run evals in a container or VM. README and runbook state this. |
| 3 | Rebuild executor | `--permission-mode bypassPermissions` lets the rebuild agent run commands unattended. | **Residual / documented** (opt-in flag; workspace is isolated and allowlist-assembled; original source and answer key withheld, post-condition checked). |
| 4 | Agentic enrichment tools (`llm/tools.py`) | Repo content is untrusted and tool results flow back into the model (prompt injection, path traversal, secret exfiltration, regex DoS). | **Mitigated**: read-only tools; paths resolved and confined to the clone; `.git`, `.env*`, keys, credential files, symlink escapes denied; size/match/time caps; results wrapped in `<repo_*>` envelopes with closing-tag escaping; system prompt declares envelopes data. Tests cover traversal, symlink, denied files, envelope escape. |
| 5 | LLM spend | Unbounded tool loops could burn money. | **Mitigated**: `--llm-max-turns`, `--llm-budget-usd`, per-request timeout, telemetry; local endpoints cost $0. |
| 6 | tree-sitter / PyYAML (new deps) | New parsing dependencies on untrusted input. | **Accepted** (ADR-001/002): parse-only, no code execution, `yaml.safe_dump`/`safe_load` only; inputs size-capped by the inventory. |
| 7 | Seed-data / DB design output | Seed values flow into generated `.sql`. | **Mitigated**: identifiers quoted, string values escaped (`_q`/`_lit`), test with embedded quotes; the file is never executed by the harvester (only by tests against in-memory SQLite). |
| 8 | Generated artifacts and secrets | Placeholders must not copy source defaults. | **Unchanged**: `.env.example` still emits placeholders, never source defaults; auth surfaces record only the *variable name* the credential is read from. Goldens in the repo contain the public demo credential of the fixtures only. |
| 9 | Test hygiene | An assertion failure echoed environment values into test output. | **Fixed** (test now compares names, never values). Operators should treat any log that captured a failing run of the earlier version of that test as sensitive. |

## Not reviewed
GUI (PySide6), clone-URL validation (covered by earlier beans), the GitHub Actions workflow (has not executed on GitHub), local-lane forge-loop.
