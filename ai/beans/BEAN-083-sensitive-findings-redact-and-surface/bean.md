# BEAN-083: Sensitive Findings — Redact Secrets/PII and Surface to the Operator

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-083 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-07-11 |
| **Started** | 2026-07-11 12:35 |
| **Completed** | 2026-07-11 13:03 |
| **Duration** | 48m |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

Verbatim capture (BEAN-082) and seed-data extraction (BEAN-066) copy exact literals from harvested repos into beans. Some of those literals will be secrets (API keys, connection strings) or PII (real emails, names in fixtures) — writing them into the requirements package violates cross-cutting safety rules 1–2 and republishes the leak into every downstream rebuild. But *silent* redaction is also wrong: a secret committed to source is a finding the repo owner needs to know about and act on (rotate credentials, scrub history). The operator must be told what was found and where — without the tool ever persisting the value itself.

Full design: `SPEC-MIRROR-MODE.md` M2.5. Flagged for Security Engineer review per cross-cutting safety rule 7.

## Goal

Every literal bound for a bean passes through detect → redact → surface: secret/PII-shaped values are replaced with typed placeholders in beans, each finding is reported to the operator (report + loud CLI warning), and the raw value is never written to any bean, log, report, or state file.

## Scope

### In Scope
- Detector module (single chokepoint, plugging into BEAN-082's seam): secret-shaped values (known key patterns e.g. `AKIA…`, high-entropy strings, connection strings/URLs with credentials) and PII-shaped values (emails, phone numbers, person-name fixture fields).
- Redaction: typed placeholders — `[REDACTED:aws-access-key]`, `[REDACTED:email]`, etc. — written wherever the literal would have appeared (bean tables, seed-data value tables from BEAN-066).
- Finding record: category (secret|PII), detector kind, `file:line` in the original repo (meaningful via BEAN-080 provenance), affected surface/bean ID, placeholder used, optional short content-hash prefix for dedup. **Never any part of the raw value.**
- Surfacing: (1) `reports/sensitive-findings.{md,json}`; (2) prominent end-of-run CLI warning — "N sensitive values were found in the source repo and redacted — see reports/sensitive-findings.md; rotate any real credentials"; (3) one-line count rollup in `REQUIREMENTS.md` (count + pointer only).
- Exit code unchanged (harvest succeeded); leave a documented seam for a future `--fail-on-secrets` gate.

### Out of Scope
- Scanning the whole repo for secrets (this filters only literals *being captured into output* — it is not a repo secret scanner like gitleaks).
- `--fail-on-secrets` CI gate (future bean if wanted).
- Rewriting/scrubbing the source repo.

## Acceptance Criteria

- [x] Fixture seeded with a fake AWS key, a DB connection string with password, and fixture emails: beans/seed tables show typed placeholders; the raw values appear **nowhere** under `<out>/` (grep-verified) nor in captured log output. *(verified live incl. the Security Engineer's docstring-planted reproduction)*
- [x] `reports/sensitive-findings.md` and `.json` list each finding with category, kind, `file:line`, affected surface, placeholder — and no value material. *(JSON has no `value` key; asserted by test)*
- [x] End-of-run CLI warning prints when findings > 0 and is absent when 0; `REQUIREMENTS.md` carries the count rollup.
- [x] Detector is a single chokepoint through which all captured literals flow — the `redact_surfaces` post-pass now recursively scans the entire enrichment structure (test-enforced; every field + nested/future keys covered).
- [x] Structlog output redacted (no PII/secret at any log level — cross-cutting rule 2 test).
- [x] Security Engineer review recorded in this bean's Notes before merge. *(see Notes: initial REJECT → fixes → APPROVE)*
- [x] All tests pass *(1943 passed)*
- [x] Lint clean *(ruff + mypy src clean)*

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Developer: redaction pass + operator surfacing | developer | BEAN-082 | Done |
| 2 | Security Engineer: mandatory review | security-engineer | 1 | Done (APPROVE) |
| 3 | Tech-QA: independent verification | tech-qa | 1, 2 | Done (PASS) |

## Notes

- Spec: `SPEC-MIRROR-MODE.md` M2.5. Operator-visibility requirement added 2026-07-11 at the operator's request: "If this was one of my repos, I would want to know."
- Depends on BEAN-082's chokepoint seam and BEAN-080's provenance for meaningful `file:line` references after cleanup.
- **Design:** redaction is a single authoritative post-pass (`harvester/redaction.py::redact_surfaces`) run after enrichment (Stage C2), before beans are written. It recursively scans every string in each surface's `enrichment` (keys preserved, values only) plus `ConfigSurface.default_value` and `SeedDataSurface.values`. Findings carry metadata only (category, kind, `file:line`, surface, placeholder, per-run-salted hash prefix) — never the raw value.

### Security Engineer sign-off (mandatory, cross-cutting rule 7)
- **Initial review: REJECT.** Proven HIGH leak — the first implementation scanned a hardcoded enrichment key *allowlist*, so a secret in a `behavioral_signals.docstring` (BEAN-054, structural) or `given_when_then` (LLM) landed raw in a bean and `surfaces.json`. Also flagged: MED hash confirmation-oracle for enumerable PII; LOW report-table injection; stale seam docstring. Tech-QA (parallel) PASS with a detector-ordering finding (connection-string mislabeled `email`).
- **Fixes:** allowlist → recursive whole-enrichment scan (closes the class by default, not by enumeration); per-run random salt on the dedup hash (oracle closed); markdown-cell escaping in the findings report; connection-string detector ordered before email; corrected the `sanitize_captured_literal` docstring. Regression tests added for docstring / given_when_then / nested / future-key vectors and the salt.
- **Re-audit: APPROVE.** Verified against the reviewer's own docstring+DSN reproduction — zero raw values on disk, structlog metadata-only. 1943 tests pass; ruff + mypy clean.
- **Known non-blocking follow-ups** (Security Engineer, explicitly NOT merge conditions): add a dashed-SSN detector; document the base64-blob high-entropy false positive (a long base64 default could be over-redacted). Worth a small follow-up bean.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Developer: redaction pass + operator surfacing | developer | — | — | — | — |
| 2 | Security Engineer: mandatory review | security-engineer | — | — | — | — |
| 3 | Tech-QA: independent verification | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 1 |
| **Total Duration** | 48m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |