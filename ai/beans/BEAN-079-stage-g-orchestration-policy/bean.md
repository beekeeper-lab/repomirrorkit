# BEAN-079: Stage G Orchestration-Policy Parameterization + Telemetry Hooks

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-079 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Stage G copies **this repo's** `.claude/` directory wholesale into every generated project folder (`assembler.py`) and hardcodes the persona roster. The user's core experiment — comparing orchestration policies (developer+tester only vs. architect-on-every-decision vs. BA-gated, across different models) — requires the generated scaffold's orchestration to be a *parameter*, not an inherited accident. Generated projects also lack standard telemetry hooks, so build-cycle runs can't be compared apples-to-apples.

## Goal

Stage G accepts an orchestration policy (YAML/flag) controlling which personas are generated, which bean types require which reviews, and what gates apply — and every generated scaffold includes standardized telemetry hooks recording per-task duration/tokens/model in a stable schema.

## Scope

### In Scope
- `--orchestration-policy <file>` (+ built-in presets: `minimal` = dev+qa, `full-team`, `architect-gated`, `ba-gated`); default preserves current behavior
- Policy schema: personas to emit, per-bean-type task templates (who picks up, who reviews, mandatory gates), escalation rules — documented + validated
- `generator/agents.py`/`assembler.py` consume the policy instead of hardcoding; stop wholesale-copying the host repo's `.claude/` (emit a curated, policy-driven set; host-repo assets only where genuinely generic)
- Telemetry hooks in generated scaffolds: pre/post task hooks writing `ai/telemetry/*.jsonl` (task id, persona, model, start/end, tokens when available) — schema aligned with BEAN-078's report format
- Policy identifier stamped into the generated CLAUDE.md + build-manifest (BEAN-069) so experiment runs are self-describing

### Out of Scope
- Running the experiments / analyzing telemetry (user-side)
- Changing THIS repo's own team workflow

## Acceptance Criteria

- [ ] `--orchestration-policy architect-gated` generates a scaffold whose task templates require architect review per bean; `minimal` yields dev+qa only
- [ ] Two scaffolds generated with different policies differ ONLY in orchestration assets (diff-tested)
- [ ] Generated telemetry hooks write valid JSONL in a smoke test
- [ ] No unrelated host-repo `.claude/` content leaks into generated scaffolds
- [ ] Policy id appears in generated CLAUDE.md and manifest
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track D
- Wave 1 — no hard deps; manifest stamping integrates with BEAN-069 when both land
- This bean is what turns "change the orchestrator's assignment strategy" from a fork into a config change
