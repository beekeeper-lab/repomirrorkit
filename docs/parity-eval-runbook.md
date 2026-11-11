# Parity eval runbook (BEAN-077/078)

Goal: measure how faithfully an agent can rebuild an application — possibly in a **different stack** — from the harvest output alone, by scoring *behaviour*, never code similarity.

## Moving parts

| Piece | Where |
|-------|-------|
| Runnable fixtures (same behaviour, two stacks) | `tests/fixtures/sample-projects/parity-flask`, `parity-express` |
| Request script + goldens | `tests/fixtures/goldens/shop.script.json`, `parity-*.golden.json` |
| Capture / score CLI | `requirements-harvester parity-capture`, `parity-score` |
| Rebuild executor | `requirements-harvester rebuild --target-stack ... --start-script` |
| Opt-in tests | `uv run pytest -m parity` (needs flask; node+npm for express) |

Scored families (weights): golden replay 0.5, Gherkin 0.3 (relative to the original when it is also run), schema 0.2. Overall is the weighted mean of the *applicable* families; the north-star gate is **90%**. Output: `parity-report.{json,md}` including run telemetry.

## Recipe

```bash
# 1. harvest the original (LLM optional)
requirements-harvester harvest --repo <git-url-or-path> --out orig-harvest --no-llm --no-fail-on-gaps

# 2. record goldens from the original (needs a request script)
requirements-harvester parity-capture --app-dir <original-dir> --script shop.script.json --out orig.golden.json \
  --env API_KEY=demo-key --auth-header "X-API-Key: demo-key"

# 3. rebuild from the harvest output ONLY (isolated workspace; answer key withheld)
requirements-harvester rebuild --from orig-harvest --workspace rebuilt --lane cloud --model sonnet \
  --permission-mode bypassPermissions --target-stack "Node.js with Express" --start-script --no-score --out eval

# 4. score
requirements-harvester parity-score --harvest-dir orig-harvest --rebuild-dir rebuilt --golden orig.golden.json \
  --original-dir <original-dir> --env API_KEY=demo-key --auth-header "X-API-Key: demo-key" \
  --rebuild-result eval/rebuild-result.json --out eval
```

The rebuild workspace is assembled by allowlist: requirement artifacts only (`beans/`, `REQUIREMENTS.md`, `api-contract.json`, `db-design/`, `screens/`, `gherkin/`, `features/`, ...). The original source (`repo/`), `surfaces.json` and the goldens are never copied.

## Cost and time

Cloud lane (`claude -p`): roughly $1–3 and 3–10 minutes per fixture with a Sonnet-class model (see `docs/rebuild-eval-2026-07-11.md` for a measured run). Scoring itself is free and takes seconds. The local lane is free but currently stalls on multi-file implementation (same doc).

## Reading a failing report

`parity-report.md` lists the failing golden interactions (expected vs actual status and the first differing fields) and the Gherkin failures. Fix the *harvest* (extractor gaps) when a rebuild repeatedly misses the same behaviour — every such miss is evidence of a recreation gap, which is what this eval exists to expose.
