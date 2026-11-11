# Task 01 — Developer: redaction pass + operator surfacing

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Depends On** | BEAN-082 (chokepoint seam) |
| **Status** | In Progress |
| **Started** | 2026-07-11 12:37 |
| **Completed** | — |
| **Duration** | — |

## Goal

Single authoritative `redact_surfaces` pass (new `harvester/redaction.py`) run
after Stage C2, before beans are written: detect secrets/PII in every
redactable surface field (incl. BEAN-082 L1 `error_contract.condition`),
replace with `[REDACTED:kind]`, record findings with file:line via
`source_ref`. Surface to operator: `reports/sensitive-findings.{md,json}`,
CLI warning, `REQUIREMENTS.md` rollup. Raw values never persisted. Exit code
unchanged.

## Definition of Done

- [ ] Conservative detectors (email, aws-access-key, private-key,
      connection-string, high-entropy, formatted phone); legitimate rule
      values NOT redacted (regression test).
- [ ] Findings carry category/kind/file:line/surface/placeholder/hash_prefix,
      never the raw value; log-safety test.
- [ ] Integration test with a throwaway planted-secret repo: raw values absent
      everywhere under out/, report present, rollup present, run still succeeds.
- [ ] Suite + ruff + mypy(src) clean.
