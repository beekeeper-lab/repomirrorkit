# BEAN-078: Rebuild Eval Harness — Parity Scoring

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-078 |
| **Status** | Unapproved |
| **Priority** | Critical |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

There is no way to know whether any of this roadmap actually improves recreation fidelity. "The beans look better" is not evidence. The keystone measurement: have an agent rebuild a fixture app **from the harvest output alone**, then score behavioral parity against the original. This is simultaneously RepoMirrorKit's quality gate and the user's telemetry rig for comparing models and orchestration policies.

## Goal

`tools/rebuild_eval/` harness: (1) harvest a fixture; (2) hand ONLY the output directory to a rebuild agent (Claude Code headless / Agent SDK) with a standard prompt; (3) score the rebuilt app — Gherkin scenario pass-rate (BEAN-074 features bound to generic HTTP steps), golden replay match-rate (BEAN-077), DB schema diff (vs BEAN-072 DDL); (4) emit a parity report with full run telemetry (duration, tokens, model, orchestration config).

## Scope

### In Scope
- Harness CLI: `rebuild-eval --fixture python-flask --model <id> [--orchestration <policy>]` → `parity-report.json` + Markdown summary
- Isolation guarantee: the rebuild agent's workspace contains the harvest output only — never the original source (the whole point)
- Scoring: Gherkin pass-rate via generic HTTP step bindings against the rebuilt app; golden request replay with field-level response diffing (ignoring declared-volatile fields); schema diff (tables/columns/FKs present)
- Telemetry: wall time, token in/out, cost estimate, per-phase breakdown — the schema deliberately matches the user's model-comparison experiment needs
- Runs as an opt-in pytest marker / manual tool (LLM cost — not default CI); one pinned smoke-eval in nightly if budget allows
- Threshold config: initial target ≥90% scenario pass-rate on fixtures documented as the north-star gate

### Out of Scope
- The orchestration policies themselves (BEAN-079 makes them configurable; experiments live outside)
- Semantic code-similarity scoring (behavioral parity only — deliberate: different-framework rebuilds shouldn't be penalized)
- Large third-party repo evals (fixtures first)

## Acceptance Criteria

- [ ] End-to-end run on `python-flask`: harvest → rebuild agent → parity report, with the rebuild workspace verifiably free of original source
- [ ] Report contains the three score families + telemetry block
- [ ] A deliberately crippled harvest (e.g. contracts stripped) scores measurably lower than a full harvest (validates the metric discriminates)
- [ ] Runbook documents cost expectations and how to run
- [ ] Lint, type-check, and pytest (non-eval suite) all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track D — the keystone; everything else exists so this number can go up
- Wave 5 — hard deps: BEAN-071, BEAN-074, BEAN-077 (soft: 072 for schema diff)
- Security: rebuild agent runs in a sandboxed/isolated workspace; Security Engineer review of the harness execution model
