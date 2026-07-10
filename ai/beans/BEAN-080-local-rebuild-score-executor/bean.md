# BEAN-080: Rebuild-and-Score Executor — Tier-1 Surface Diff

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-080 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-07-10 |
| **Started** | 2026-07-10 |
| **Completed** | 2026-07-10 |
| **Duration** | ~1 session |
| **Owner** | forge (Forge improvements program, WP-3.4) |
| **Category** | App |

## Problem Statement

RepoMirrorKit's north star — "requirements sufficient to *recreate* the
project" — is unverified: there is no rebuild step and no score. BEAN-078 is
the eventual keystone (behavioral parity: Gherkin pass-rate, golden replay,
schema diff), but it is Wave-5 work blocked behind BEAN-071/074/077 and cannot
start now. Meanwhile the Forge program (IMP-09 / WP-3.4) needs a runnable
`rebuild → score` loop *today* to serve as its frontier-vs-local test bench.

## Goal

The buildable-now first slice: a rebuild executor (cloud lane) plus the
cheapest scoring tier — **surface re-extraction diff** — as a runnable loop:

    harvest  →  rebuild(lane)  →  re-harvest  →  score

reusing the harvester's own extraction to answer "did the rebuild reproduce
the same routes, models, APIs, auth surfaces?"

## Scope

### In Scope
- `harvester/rebuild/executor.py`: assemble an isolated rebuild workspace
  (allowlist of requirement artifacts only — never the original `repo/` or the
  `surfaces.json` answer key), drive the cloud lane (`claude -p`), record
  telemetry (wall time, tokens, cost, turns), `git init` the result.
- `harvester/rebuild/scoring.py`: parse two `surfaces.json` files, compute
  per-surface-type + micro-averaged precision/recall/F1, emit
  `rebuild-score.{json,md}`.
- CLI verbs: `rebuild` (full loop) and `score` (diff two harvests).

### Out of Scope
- Local lane (forge-loop) — seam is in place, raises pending WP-3.5.
- Behavioral parity scoring (tiers 2–3) — that is BEAN-078.
- Actually running a cloud rebuild end-to-end — that is Forge WP-3.5.

## Acceptance Criteria

- [x] Rebuild executor works for the cloud lane (subprocess boundary injectable).
- [x] Scoring tier 1 implemented; discriminates (identical harvest → 100%,
      dropped-route harvest → 87.5% recall / 100% precision on the flask fixture).
- [x] Workspace isolation enforced by allowlist + post-condition check.
- [x] Unit tests (19 new); full suite green (1858 passed).
- [x] Lint + type-check clean.

## Notes

- Forge-side brief: `docs/improvements/IMP-09-rmk-rebuild-score.md` in the
  forgeSetup repo (WP-3.4). Precursor to BEAN-078 (surface diff = scoring
  tier 1; Gherkin/golden/schema = tiers 2–3).
- Local Ollama enrichment path (IMP-09 §3a) lives on the unmerged
  `bean/local-llm-endpoint` branch; the local rebuild lane will build on it.
