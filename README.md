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

The harvester runs an 8-stage pipeline (clone → inventory + framework detection → 14 surface analyzers → optional LLM enrichment → traceability → bean generation → coverage gates → Claude Code project folder) and writes the results under `--out`. LLM enrichment is on by default (`--llm`): with an `ANTHROPIC_API_KEY` in the environment, beans are enriched with behavioral descriptions, acceptance criteria, and inferred intent. Without the key, the run falls back to structural-only output with a warning; pass `--no-llm` to skip enrichment silently.

Enrichment is **agentic** by default: the model gets read-only `read_file` / `grep` / `list_dir` tools over the clone (sandboxed; secrets and `.git` are unreadable) and traces each surface end-to-end, recording `confidence`, `gaps` and a `traced_flow`. Caps: `--llm-max-turns` (default 8) and `--llm-budget-usd` (default 5.0, estimate; local endpoints cost $0). Use `--no-llm-agentic` for the single-shot prompt. Per-surface token/cost telemetry lands in `reports/enrichment-telemetry.json`. Static (`declared`/`inferred`) extraction is never overwritten by model output. Stages A, B, C and C2 are persisted under `<out>/state/`, so `--resume` and `--from-stage C2` do not re-pay for earlier work.

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
```
