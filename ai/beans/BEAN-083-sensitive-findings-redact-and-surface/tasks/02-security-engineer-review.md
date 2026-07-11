# Task 02 — Security Engineer: mandatory review

| Field | Value |
|-------|-------|
| **Owner** | security-engineer |
| **Depends On** | 01 |
| **Status** | Done (APPROVE) |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Cross-cutting rule 7 requires Security Engineer sign-off before merge. Verify:
raw secret/PII values leak NOWHERE (beans, logs, reports, state); detector
false-negative surface (what secret shapes slip through) and false-positive
surface (legitimate data wrongly redacted); hash_prefix cannot reconstruct the
value; the redaction pass covers every literal-bearing field including the
BEAN-082 L1 condition descriptor. Record explicit APPROVE/REJECT in bean notes.
