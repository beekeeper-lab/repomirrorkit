# Rebuild eval — cross-stack parity (2026-11-11)

First behavioural-parity runs of the recreation pipeline (BEAN-077/078). Each rebuild was produced by `claude -p --model sonnet` from the harvest output **alone** (isolated workspace; original source, `surfaces.json` and the goldens withheld) into a **different** technology stack, then scored by running the rebuilt app and replaying the original's recorded behaviour.

Fixtures: two runnable orders APIs with identical observable behaviour in different stacks — `parity-flask` (Flask + SQLAlchemy) and `parity-express` (Express) — featuring API-key auth, validation with error messages, a status workflow (draft → submitted → paid / cancelled), a seeded lookup table, and 404/409 handling. 20 recorded interactions; the two originals produce byte-identical goldens, which is also what proves the harness is framework-neutral.

| Run | Overall | Golden replay | Gherkin (relative to original) | Schema | Wall | Cost | Turns |
|-----|--------:|---------------|-------------------------------|--------|-----:|-----:|------:|
| Flask → Node/Express (new harvest) | 100% | 100% (20/20) | 100% (13/14 bound) | N/A | 35s | $0.23 | 7 |
| Express → FastAPI (new harvest) | 100% | 100% (20/20) | 100% (13/14 bound) | N/A | 86s | $0.25 | 12 |
| Flask → Node/Express (baseline harvest: code before this work) | 25% | 10% (2/20) | 50% (6/14 bound) | N/A | 30s | $0.19 | 7 |

Gate: overall ≥ 90%. Schema is N/A when the rebuild has no relational database design (storage is an implementation choice). Raw reports: `docs/eval-results/`.

## What this shows

- **The harvest is now sufficient to recreate this API in another stack.** Both new-harvest rebuilds reproduce all 20 recorded interactions exactly — including auth, validation messages, the workflow guards and the seeded categories — in 30–90 seconds and about $0.25 each.
- **The metric discriminates.** The same prompt, model and target stack, fed the harvest produced by the pre-work code (10 beans, *no API surfaces detected* for this Flask app), scores 25% overall / 10% golden replay.
- The jump is attributable to specific extractor work driven by this eval: Flask verb shorthand and app-factory routes, handler-level credential detection, status/error extraction through helpers, imperative-validation mining, per-route Express auth, serializer-method response shapes, module-level seed lists, and the contract/OpenAPI/Gherkin/DB artifacts that carry them to the rebuilder.

## Honest limits

- Two small fixtures, API-only, no UI. Screens/forms are extracted and specified but not behaviourally scored yet.
- One run per cell (no variance estimate); one model (Sonnet-class). Cost/time are single measurements.
- The Gherkin family binds only the API-level phrasing (14 of ~47 scenarios bind; the rest — rules, invariants, workflows, screens — are reported as unbound, never counted as passes). Calibration against the original keeps ambiguous scenarios from penalising a rebuild.
- LLM enrichment was **off** for every harvest here (no API key; local endpoint unavailable), so these numbers are the structural floor. Agentic enrichment (BEAN-068) is implemented and unit-tested but has not been run live.
- The fixtures were fixed alongside the extractors; a held-out real-world app is the right next test (see `docs/real-world-triage-microblog.md`).

## Reproduce

See `docs/parity-eval-runbook.md`. In short: `harvest` → `rebuild --target-stack ... --start-script` → `parity-score`. Offline tests: `uv run pytest -m parity`.
