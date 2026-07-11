# BEAN-068: Agentic Enrichment v2 — Repo-Aware Feature Tracing

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-068 |
| **Status** | Unapproved |
| **Priority** | Critical |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Current enrichment (`llm/enrichment.py`) is one-shot per surface: ≤3 code snippets, 4,000 chars each, no cross-surface context, no ability to look anywhere else in the repo. It can describe a route in isolation; it cannot trace "submit button → validation → API call → service → model write" — precisely the knowledge functional recreation requires. It also cannot fill gaps static extraction leaves (dynamic routes, computed contracts, imperative business rules).

## Goal

Replace snippet prompting with an agentic enrichment pass: Claude gets read/grep/list tools over the cloned repo plus the full surface map, traces each surface's feature end-to-end, fills contracts/rules/mappings static analysis missed, and explicitly records what it could not determine. Cost-controlled via the Batch API and per-run budgets.

## Scope

### In Scope
- Tool-use loop in `llm/` (read_file / grep / list_dir over the workdir, sandboxed to the clone, size-capped) — either direct tool-use via the `anthropic` SDK or the Agent SDK; architect decides (ADR)
- Enrichment unit = surface + its cross-referenced neighbors (route + components + APIs + models), not one surface blind
- Output schema extends today's enrichment: adds `gaps: list[str]`, `confidence`, `traced_flow` (ordered hop list with file refs); merges into surfaces without overwriting higher-confidence static extraction
- Batch API path for large repos; `--llm-budget-usd` / max-turns per surface caps; per-surface failure isolation (existing behavior preserved)
- Bump default model to the current Sonnet generation; keep `--llm-model` override
- Prompt-injection posture preserved: tool results are repo-derived → wrapped in `<repo_*>` envelopes with the existing SECURITY DIRECTIVE; tools are read-only
- Unit tests with a mocked client; integration test gated on `ANTHROPIC_API_KEY` presence

### Out of Scope
- Feature clustering / synthesis (BEAN-069)
- Caching LLM responses across runs (nice-to-have; note as follow-up)
- Write-tools of any kind for the enrichment agent

## Acceptance Criteria

- [ ] Enrichment agent can answer from files NOT in the surface's `source_refs` (proved by a fixture where the response shape lives in a service file)
- [ ] Every enriched surface carries `confidence` and an explicit `gaps` list (empty allowed)
- [ ] Static `declared`-confidence extraction is never overwritten by lower-confidence LLM output
- [ ] Budget cap halts enrichment gracefully with per-surface status recorded
- [ ] Token/cost telemetry per surface and per run written to `reports/enrichment-telemetry.json`
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track B — the biggest single lever
- Wave 1–2 — soft dep: BEAN-060 (persisted outputs make iterating affordable; strongly recommended first)
- Security Engineer review required (LLM + untrusted repo content + tools)
- Telemetry here doubles as the model-comparison rig data source
