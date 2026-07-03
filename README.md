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
