# BEAN-084: Redaction Detector Follow-ups (SSN + base64 False Positive)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-084 |
| **Status** | Unapproved |
| **Priority** | Low |
| **Created** | 2026-07-11 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The BEAN-083 Security Engineer review APPROVED the redaction feature but noted two
non-blocking follow-ups worth tracking:

1. **Missing dashed-SSN detector.** `123-45-6789`-style SSNs are not currently
   detected/redacted. Specific pattern, low false-positive risk — reasonable to add.
2. **Base64-blob high-entropy false positive.** A long base64 literal (e.g. an
   inline data URI or asset blob) in a captured default can exceed the
   high-entropy threshold (>4.0 bits/char, ≥32 chars) and be wrongly redacted to
   `[REDACTED:high-entropy-secret]`, silently corrupting a legitimate captured
   value. This is the fidelity risk `SPEC-MIRROR-MODE.md` §6 called out.

## Goal

Reduce redaction false negatives (SSN) and false positives (base64 blobs) without
regressing the conservative, low-false-positive posture of the BEAN-083 detectors.

## Scope

### In Scope
- Add a dashed-SSN detector (`\d{3}-\d{2}-\d{4}`, category PII) to `_DETECTORS`.
- Guard the high-entropy detector against decodable base64 blobs (e.g. skip when
  the match decodes to valid binary of a plausible asset size, or exempt strings
  that are pure base64 above a length that indicates a blob rather than a token).
- Tests: SSN positive/negative; a base64 asset blob is NOT redacted while a real
  high-entropy token still is.

### Out of Scope
- Broadening secret detection generally (short secrets, provider-token prefixes) —
  deferred; the high-entropy sweep already catches ≥32-char provider tokens.
- Any change to the redaction architecture (the `redact_surfaces` post-pass).

## Acceptance Criteria

- [ ] Dashed SSNs are redacted to `[REDACTED:ssn]` with a PII finding.
- [ ] A representative base64 asset blob survives un-redacted; a genuine
      high-entropy secret is still redacted.
- [ ] Legitimate BEAN-081/082 values remain un-redacted (regression).
- [ ] All tests pass; lint + mypy clean.

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.

## Notes

- Origin: BEAN-083 Security Engineer sign-off (2026-07-11), explicitly flagged as
  non-blocking follow-ups. See BEAN-083 Notes.

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
