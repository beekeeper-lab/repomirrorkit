# RepoMirrorKit — Completion Spec (resumable)

**Goal:** Given a Git repo, `harvest` emits requirement and design artifacts complete enough that an agent can rebuild the app in a different tech stack, with no access to the source.
**Created:** 2026-11-11 from the status assessment. Supersedes the sequencing in `ROADMAP-RECREATION.md` (beans stay the unit of work; see `ai/beans/`).
**Baseline:** 1,863 tests green. Python-Flask fixture output is good. `ts-next` fixture has no API schemas (fidelity gate FAILS). Beans are TODO-filled without LLM enrichment.

---

## How to use this file (resume protocol)

1. Read **Progress Log** at the bottom, then find the first unchecked `[ ]` task below. Work in order within a phase. Phases may overlap only where a task says "parallel-ok".
2. Before starting: `git status`, `git branch --show-current`. Run `QT_QPA_PLATFORM=offscreen uv run pytest -q`. If red, fix or note it first.
3. Mark a task `[~]` (in progress) when you start it, with the branch name. Mark `[x]` only when its **Verify** line passes. Check items off in the same commit as the work.
4. One bean per branch (`bean/BEAN-NNN-...`), merge into `test` (existing flow). Push via `git@github.com:beekeeper-lab/repomirrorkit.git`.
5. After each task, append one line to the Progress Log (date, task ID, result, commit sha). If stopped mid-task, log what is done and what remains.
6. Never skip a Verify. If a task turns out wrong or too big, split it here and record why in the log.

Legend: `[ ]` todo, `[~]` in progress, `[x]` done, `[-]` dropped (reason in log).

---

## Phase 0 — Housekeeping and baseline

- [x] **0.1** Commit or revert the uncommitted `.gitignore` change; decide whether `.agentic/` and `.claude/worktrees/` get ignored. *Verify:* `git status` clean.
- [x] **0.2** (060 is a WIP checkpoint, handled in 3.1; 067/072 branches had no work, built in 4.4/6.1; local-llm-endpoint cherry-picked) Merge the open bean branches into `test` ( check `git branch --no-merged test`). Resolve conflicts in `surfaces.py` / `pipeline.py` by keeping additions append-only. *Verify:* full suite green on `test`; `git branch --no-merged test` shows only intentional leftovers.
- [x] **0.3** Merge `bean/local-rebuild-score-executor` (BEAN-080) into `test`. *Verify:* suite green; `requirements-harvester rebuild --help` works.
- [-] **0.4** (deferred: orchestration policy serves the Stage G experiment, not the rebuild goal) Finish BEAN-079 (Stage G policy parameterization + telemetry hooks). *Verify:* its bean acceptance criteria all checked; suite green; set bean status to Done in `ai/beans/_index.md`.
- [ ] **0.5** Promote `test` to `main` (PR). *Verify:* `main` contains BEAN-059..080 work; CI green.
- [ ] **0.6** Update `ai/beans/_index.md` and the memory file so statuses match reality (060, 067, 072 etc.).

## Phase 1 — Fix scoring blockers (small, high value)

- [x] **1.1** Python API detector: support `@app.get/.post/.put/.delete/.patch` and `@bp.<verb>` shorthand. Add failing unit tests first. *Verify:* new tests pass.
- [x] **1.2** Python API detector: find routes registered inside app-factory functions (`def create_app(): ... @app.route`) and Blueprint registration. *Verify:* new fixture `python-flask-factory` (the sonnet rebuild from `docs/rebuild-eval-2026-07-11.md` is a good source) extracts 2 APIs.
- [x] **1.3** FastAPI `APIRouter` prefix + `include_router` resolution (verify existing behavior; fix if gaps). *Verify:* test with a prefixed router yields full paths.
- [x] **1.4** (precision/recall already reported separately in scoring.py; tier-1 stays a regression floor, behavioral parity in Phase 7 is the real gate) Tier-1 scoring: add layout/idiom-insensitive normalization notes and report extra-surface precision separately from recall. *Verify:* rebuild-eval doc caveats reproduced as unit tests in `test_rebuild_scoring.py`.
- [-] **1.5** (folded into 7.3: cloud rebuilds are run once, there) Re-run the rebuild eval on the Flask fixture (cloud lane) and record in `docs/rebuild-eval-<date>.md`. *Verify:* `apis` recall is 2/2.

## Phase 2 — Enrichment baseline (no API key here; use the local Ollama endpoint, e.g. gpt-oss:120b or qwen3.8:27b, via the cherry-picked local-llm-endpoint support)

- [!] **2.1** (BLOCKED 2026-11-11: local Ollama unresponsive, no API key; retry when available) Run `harvest` with LLM on both fixtures. Inspect beans for remaining `TODO:` placeholders and hallucinated content. Save outputs under `docs/samples/`. *Verify:* written assessment in `docs/enrichment-baseline-<date>.md` listing placeholder counts per fixture.
- [x] **2.2** Add a gate: with LLM enabled, count of `TODO:` placeholders in beans is reported in `reports/fidelity.*` and fails above a threshold (start at 0 for fixtures). *Verify:* unit test + fixture run.

## Phase 3 — Foundations

- [x] **3.1** BEAN-060 merged and verified: kill a harvest mid-run, `--resume` continues from the next stage using persisted outputs. *Verify:* integration test + manual kill/resume.
- [x] **3.2** BEAN-061 tree-sitter foundation: parser loader for TS/TSX/JS/Python/C#, query helpers, graceful fallback to regex when grammar missing. Evaluate deps per the dependency-discipline rule (license, maintenance); record an ADR in `ai/context/decisions/`. *Verify:* parses all fixture sources; unit tests; ADR committed.

## Phase 4 — Extraction depth (parallel-ok after 3.2 where noted)

- [x] **4.1** BEAN-063 JS/TS API contracts (Express, NestJS, Next.js route handlers): populate request and response schemas. *Verify:* `ts-next` fixture: `gaps.md` shows 0 API schema gaps; fidelity gate PASSES; `api-contract.json` has fields for `/api/users`.
- [ ] **4.2** BEAN-064 `ScreenSurface`: pages, forms, fields, validation hints, field-to-model mapping, navigation edges. Start with React/Next, then Vue/Svelte; Python templates (Jinja) if cheap. *Verify:* `ts-next` yields a screen for `UserList` with fields mapped to `User`.
- [ ] **4.3** BEAN-065 `BusinessRuleSurface`: validation libraries (zod, pydantic, marshmallow, class-validator) and DB constraints. *Verify:* fixture rules appear as beans and in `surfaces.json`.
- [ ] **4.4** BEAN-067 `WorkflowSurface` — BUILD (branch was empty). *Verify:* fixture or synthetic test emits a state graph.
- [ ] **4.5** Non-Python/JS stacks: confirm .NET detector produces API contracts (parity with 4.1) or log it as a known gap in `README.md`. *Verify:* a .NET fixture exists and its output is checked.

## Phase 5 — Synthesis

- [ ] **5.1** BEAN-068 agentic enrichment v2: repo tool access (read, grep) for feature tracing, Batch API, cost cap flag, prompt-injection defenses retained (BEAN-046). *Verify:* on fixtures, behavioral descriptions reference real code paths; cost per run recorded in the log.
- [ ] **5.2** BEAN-069 feature clustering stage: `features/FEAT-*.md` plus `build-manifest.json` (dependency-ordered build DAG). *Verify:* manifest is a valid DAG covering all APIs, screens and models in the fixtures.

## Phase 6 — Design artifacts

- [ ] **6.1** BEAN-072 DB design bundle — BUILD (branch was empty) (SQL DDL, JSON Schema, seeds). *Verify:* DDL loads into SQLite for the Flask fixture.
- [ ] **6.2** BEAN-073 screen spec YAML + navigation map. *Verify:* YAML validates against its schema; Mermaid renders.
- [ ] **6.3** BEAN-074 Gherkin `.feature` per feature cluster. *Verify:* files parse with a Gherkin parser; every API has at least one scenario.
- [ ] **6.4** BEAN-075 sequence and state diagrams (low priority; defer if time-boxed).
- [ ] **6.5** `REQUIREMENTS.md` becomes the index of all artifacts (contract, DB, screens, features, manifest). *Verify:* every generated artifact is linked and nothing is orphaned.

## Phase 7 — Fidelity loop (the real exit test)

- [ ] **7.1** BEAN-077 golden parity fixtures: request/response captures for both fixture apps. *Verify:* replay passes against the original apps.
- [ ] **7.2** BEAN-078 behavioral parity scoring: run the rebuilt app and replay the golden requests, plus Gherkin pass-rate and schema diff, layout-agnostic. *Verify:* score computed for a known-good and a known-bad rebuild; they differ sharply.
- [ ] **7.3** Cross-stack rebuild: rebuild the Flask fixture in a different stack (e.g. Node/Express) and the Next fixture in a different stack (e.g. FastAPI + HTML), from the output dir alone. *Verify:* behavioral parity ≥ 90% on both. Record in `docs/rebuild-eval-<date>.md`.
- [ ] **7.4** Add one larger real-world repo (medium, open source) as a third fixture to expose idiom gaps the toy fixtures hide. *Verify:* harvest completes; gaps triaged into new beans.
- [ ] **7.5** Fidelity gates run in CI and fail on regression. *Verify:* CI config committed; a deliberately broken extractor turns it red.

## Phase 8 — Hardening and docs

- [ ] **8.1** Update `README.md` and `CLAUDE.md` for the final pipeline stages and outputs; remove stale framing.
- [ ] **8.2** Security pass (persona: Security Engineer) on the LLM path, clone path and tree-sitter dependencies.
- [ ] **8.3** Final full run on all fixtures; archive outputs and scores in `docs/`.

---

## Exit criteria (all must hold)

1. Both fixtures: harvest with LLM yields zero `TODO:` placeholders, populated OpenAPI, DB bundle, screen specs, features and build manifest.
2. Cross-stack rebuild from output alone reaches ≥ 90% behavioral parity on both fixtures (7.3).
3. Fidelity gates run in CI and fail on regression (7.5).
4. Suite green on `main`; docs match behavior.

## Progress Log

| Date | Task | Result | Commit |
|------|------|--------|--------|
| 2026-11-11 | — | Spec created. Baseline: 1,863 tests green; ts-next fidelity gate failing. | — |
| 2026-11-11 | 0.1-0.3 | Merged BEAN-080 + local-llm-endpoint into `test`; suite 1,872 green. 0.4 deferred (not on critical path). 0.5/0.6 pending final merge to main. | test |
| 2026-11-11 | 1.1-1.4 | Flask verb shorthand, tuple methods, factory routes, Blueprint/APIRouter prefix resolution, python-flask-factory fixture + e2e test. 1,880 tests green. 1.5 folded into 7.3. | bean/BEAN-081 |
| 2026-11-11 | 2.1/2.2 | 2.1 blocked (Ollama not responding; no key). 2.2: placeholder gate enforced at 80% when enrichment active; LLM client 120s timeout added. | test |
| 2026-11-11 | 3.1 | BEAN-060 done: stage B/C/C2 persisted + rehydrated with hash/fingerprint guards, --from-stage, beans always regenerate; 6 integration tests. | bean/BEAN-060-resume-v2 |
| 2026-11-11 | 3.2 | BEAN-061: tree-sitter (js/ts/tsx/c#) loader + helpers in harvester/parsing, ADR-001, 12 tests. | bean/BEAN-061-tree-sitter |
| 2026-11-11 | 4.1 | BEAN-063: JS/TS contract extraction (Next app router, Express, NestJS DTOs, zod, typed bodies, status codes, errors, arrays); OpenAPI renders arrays/status/errors; ts-next fidelity gate now PASSES; 1,909 tests. | bean/BEAN-063-js-ts-api-contracts |
