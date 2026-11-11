# RepoMirrorKit

A **requirements harvester**: point it at a Git repository and it produces structured requirement artifacts ("beans"), coverage reports, and a Claude Code project scaffold derived from the source code. The CLI (`requirements-harvester`) is the primary entry point; a small PySide6 GUI wraps it for quick interactive runs.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Create virtual environment
uv venv

# Install the package with dev dependencies
uv pip install -e ".[dev]"
```

## Run

### CLI (primary)

```bash
# Harvest a public repo to a chosen output directory
uv run requirements-harvester harvest \
    --repo https://github.com/some-user/some-project.git \
    --out /tmp/harvest-out

# Show all flags
uv run requirements-harvester harvest --help
```

The goal is **recreation**: the output should be enough for an agent to rebuild the application — possibly in a different tech stack — without seeing the source. The harvester runs a 9-stage pipeline (A clone → B inventory + framework detection → C surface analyzers → C2 optional LLM enrichment → C3 feature clustering → D traceability → E beans, features and build manifest → F coverage + fidelity gates → G design artifacts and Claude Code project folder) and writes the results under `--out`. LLM enrichment is on by default (`--llm`): with an `ANTHROPIC_API_KEY` in the environment, beans are enriched with behavioral descriptions, acceptance criteria, and inferred intent. Without the key, the run falls back to structural-only output with a warning; pass `--no-llm` to skip enrichment silently.

**No API key? Use your Claude Code login:** `--llm-backend claude-cli` runs headless `claude -p` per surface (read-only `Read`/`Grep`/`Glob`, scrubbed environment, `ANTHROPIC_API_KEY` deliberately removed so the subscription is used), e.g. `harvest ... --llm --llm-backend claude-cli --llm-model sonnet --llm-concurrency 4`. Only behavioural surface types are sent (APIs, models, screens, auth, workflows, ...). Reported costs are API-equivalent estimates that consume plan usage; a small fixture (13 surfaces) took about a minute. The path sandbox is weaker than the API backend's (deny rules, best effort) — prefer `--llm-backend api` for repos you don't trust. Enriched beans never copy secret values (prompt rule; config defaults for key/token/secret variables are withheld).

Enrichment is **agentic** by default: the model gets read-only `read_file` / `grep` / `list_dir` tools over the clone (sandboxed; secrets and `.git` are unreadable) and traces each surface end-to-end, recording `confidence`, `gaps` and a `traced_flow`. Caps: `--llm-max-turns` (default 8) and `--llm-budget-usd` (default 5.0, estimate; local endpoints cost $0). Use `--no-llm-agentic` for the single-shot prompt. Per-surface token/cost telemetry lands in `reports/enrichment-telemetry.json`. Static (`declared`/`inferred`) extraction is never overwritten by model output. Stages A, B, C and C2 are persisted under `<out>/state/`, so `--resume` and `--from-stage C2` do not re-pay for earlier work.

### What you get

| Output | Purpose |
|--------|---------|
| `REQUIREMENTS.md` | Front door: design-artifact index, features in build order, every surface |
| `beans/` | One requirement file per surface (APIs with contracts/errors/auth, models, screens, business rules, workflows, seed data, config, ...) |
| `api-contract.json` | OpenAPI 3.1: request/response fields, validation constraints, status codes, error responses, auth scheme |
| `db-design/` | `schema.sql` (loads into SQLite), JSON Schema per entity, seed data |
| `screens/` | Versioned YAML spec per screen (fields, validation, field→API→model bindings, actions) + navigation map |
| `gherkin/` | Behaviour scenarios (`.feature`) per feature, tagged to beans |
| `features/`, `build-manifest.json` | Vertical slices and a dependency-ordered build plan (JSON-schema validated, deterministic) |
| `diagrams/` | Mermaid state and sequence diagrams rendered from the specs |
| `reports/` | Coverage, **fidelity** (recreation-readiness) gates, gaps |

Supported depth today: Python (Flask/FastAPI, WTForms, SQLAlchemy 1.x/2.0), JS/TS (Next.js, Express, NestJS, zod/class-validator, React/Vue/Svelte forms), ASP.NET (controllers, minimal APIs, DataAnnotations). See `docs/real-world-triage-microblog.md` for known gaps.

### Measure fidelity: rebuild and score

```bash
# Rebuild from the harvest output alone into another stack, then score behavioural parity
uv run requirements-harvester rebuild --from out --workspace rebuilt --lane cloud --model sonnet \
    --permission-mode bypassPermissions --target-stack "Node.js with Express" --start-script --no-score
uv run requirements-harvester parity-score --harvest-dir out --rebuild-dir rebuilt --golden orig.golden.json \
    --original-dir <original-app> --out eval
```

Scores golden request/response replay, generated Gherkin scenarios (calibrated against the original) and database schema; gate ≥ 90%. See `docs/parity-eval-runbook.md` and the first results in `docs/rebuild-eval-2026-11-11.md`. **Security:** the rebuilt app is LLM-generated, untrusted code — `parity-score` runs it with a scrubbed environment (no host secrets), but run evals in a container or VM; `--permission-mode bypassPermissions` lets the rebuild agent execute commands unattended.

### GUI (interactive launcher)

```bash
uv run python -m repo_mirror_kit
```

The GUI wraps a subset of CLI options (clone + harvest) and is intended as a quick-start surface; for advanced configuration (LLM enrichment, custom include/exclude globs, resume, file size limits) use the CLI.

## Development

```bash
# Lint
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/

# Type check
uv run mypy src/

# Tests
uv run pytest                       # full suite (unit + integration)
uv run pytest -m "not integration"  # unit-only (faster)
uv run pytest -m integration        # end-to-end pipeline tests against fixtures
uv run pytest -m parity             # boots the runnable Flask/Express fixtures (needs node+npm)
scripts/fidelity-gate.sh            # harvest every fixture; fail if a fidelity gate is missed (CI)
```

## License

MIT — see [LICENSE](LICENSE).
