# Rebuild-eval — first frontier-vs-local comparison (2026-07-11)

First run of the BEAN-088 rebuild-and-score loop (Forge WP-3.5 / IMP-09 §4).
One fixture, harvested once, rebuilt by two lanes from the requirement
artifacts **alone**, each re-harvested and scored by the tier-1 surface
re-extraction diff.

- **Fixture:** `tests/fixtures/sample-projects/python-flask` (2 API endpoints
  on `/api/users`, a `User` model + `UserStatus` enum, seed SQL, one test).
- **Harvest:** structural-only (`--no-llm`; no `ANTHROPIC_API_KEY` present) →
  8 surfaces, 8 beans, `REQUIREMENTS.md`, `api-contract.json`, `data-model.md`,
  a `project-folder/` scaffold. Both lanes got the identical inputs; the
  original source and the `surfaces.json` answer key were withheld by the
  executor's allowlist.

## Result

| Lane | Model | Outcome | Wall | Cost | Turns/Steps | Retries | Tier-1 recall | precision | F1 |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| Cloud | `sonnet` (`claude -p`) | **built a working app** | 212 s | $1.02 | 39 | — | 75% (6/8) | 35% (6/17) | 48% |
| Local | `gemma4:26b` (forge-loop) | **escalated** | 862 s | $0 | 6 planned | 3 | 0% (0/8) | 0% (0/10) | n/a |

## Cloud lane — success, with two scoring caveats

`sonnet` built a complete Flask app in 212 s / $1.02 / 0 interventions:
app-factory `create_app()` in `src/app.py`, `models.py`, `seeds.py`,
`tests/`, `pyproject.toml`, `wsgi.py`. It is a *more* complete project than
the fixture. Two things drag the tier-1 number below the app's real fidelity:

1. **`apis` scored 0/2 — but both endpoints exist.** The rebuild wrote
   `@app.get("/api/users")` and `@app.post("/api/users")` inside the
   `create_app()` factory. RMK's Python API detector only recognises the flat,
   module-level `@app.route(..., methods=[...])` idiom the fixture used, so it
   re-extracted **zero** APIs from a faithful rebuild. This is a harvester
   extraction gap, **not** a build failure — and the single most important
   finding of the run (see below).
2. **Precision penalised for being thorough.** The rebuild emitted 17 surfaces
   to the original's 8 (extra deps, extra tests, `general_logic` from the
   factory/seeds code). Tier-1 rewards *sameness*, so a richer rebuild loses
   precision. Recall on the surfaces it *could* re-extract was 100% for models,
   deps, tests, and seed data.

Net: the 48% F1 understates a rebuild that a human would call faithful.
Tier-1 is a floor, not a verdict — which is the argument for BEAN-078's
behavioural parity (run the app, hit the endpoints; layout-agnostic).

## Local lane — escalated, reproducing gemma4's known ceiling

`gemma4:26b` under forge-loop planned six coherent steps (deps → models →
services → routes → …), passed step 1 (`requirements.txt` + `pip install`),
then **failed step 2 (implement `models.py`) three times and escalated** at
862 s. The escalation's "last feedback" block was empty — the exact
**empty-completion pattern on implement prompts** already recorded for gemma4
in the model registry (2026-07-04). It committed only `requirements.txt`, so
its re-harvest scored 0% recall.

This is a faithful reproduction of the documented limit in a new context, and
it matches the L3 study-deck arc: gemma4 plans well and does trivial steps, but
stalls on real multi-file implementation and must escalate. The designed
remedy — escalate to `gpt-oss:120b` — was **not** exercised here (the ladder is
still a manual model switch; automating it is the top forge-loop follow-up).
Re-running `forge-loop run --model gpt-oss:120b` resumes from step 2 and is the
obvious next experiment.

## Findings

1. **Actionable RMK bug (highest value):** the Python API analyzer misses
   `@app.get`/`@app.post` shorthand and routes defined inside an app-factory
   function. A large class of idiomatic Flask apps re-extracts as zero APIs.
   Feeds BEAN-062 (API contract extraction). Until fixed, tier-1 recall on
   `apis` is unreliable for any rebuild that doesn't mirror the source idiom.
2. **Tier-1 has two systematic biases** — idiom/layout sensitivity (finding 1)
   and a precision penalty for thoroughness. Both are inherent to a
   surface-count diff and both argue for behavioural parity (BEAN-078) as the
   real gate. Tier-1 is a cheap regression floor, not a fidelity verdict.
3. **The lanes are asymmetric today:** cloud completes an app rebuild solo;
   local (gemma4) cannot and escalates early. A fair local number needs the
   two-model escalation ladder (gemma4 builder → gpt-oss:120b fixer) wired end
   to end.
4. **The harness itself worked:** workspace isolation held (neither agent saw
   the source or answer key), telemetry captured (cost/turns for cloud,
   steps/retries for local), and the failed local rebuild was correctly *not*
   scored by the `rebuild` verb — the number in the table came from a manual
   `score` on the partial output.

## Reproduce

```bash
# harvest once (git-init a copy of the fixture first)
requirements-harvester harvest --repo <fixture-git> --out orig-harvest --no-llm --no-fail-on-gaps
# cloud lane
requirements-harvester rebuild --from orig-harvest --workspace rebuild-cloud \
  --lane cloud --model sonnet --permission-mode bypassPermissions --out eval-cloud
# local lane
requirements-harvester rebuild --from orig-harvest --workspace rebuild-local \
  --lane local --model gemma4:26b-a4b-it-q4_K_M --data-class public \
  --allow "python3 -m pytest" --allow python3 --allow pip --out eval-local
```
