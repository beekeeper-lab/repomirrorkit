# BEAN-083: Sensitive Findings — Redact Secrets/PII and Surface to the Operator

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-083 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-07-11 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
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

- [ ] Fixture seeded with a fake AWS key, a DB connection string with password, and fixture emails: beans/seed tables show typed placeholders; the raw values appear **nowhere** under `<out>/` (grep-verified in test) nor in captured log output.
- [ ] `reports/sensitive-findings.md` and `.json` list each finding with category, kind, `file:line`, affected bean, placeholder — and no value material.
- [ ] End-of-run CLI warning prints when findings > 0 and is absent when 0; `REQUIREMENTS.md` carries the count rollup.
- [ ] Detector is a single chokepoint through which all BEAN-082 and BEAN-066 literals flow (test-enforced).
- [ ] Structlog output redacted (no PII/secret at any log level — cross-cutting rule 2 test).
- [ ] Security Engineer review recorded in this bean's Notes before merge.
- [ ] All tests pass
- [ ] Lint clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Spec: `SPEC-MIRROR-MODE.md` M2.5. Operator-visibility requirement added 2026-07-11 at the operator's request: "If this was one of my repos, I would want to know."
- Depends on BEAN-082's chokepoint seam (soft — the seam can be added here if 082 hasn't landed) and BEAN-080's provenance for meaningful `file:line` references after cleanup.

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
