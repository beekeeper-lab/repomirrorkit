# RepoMirrorKit

A desktop tool for mirroring git repositories, built with Python and PySide6.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Create virtual environment
uv venv

# Install the package with dev dependencies
uv pip install -e ".[dev]"
```

## Run

```bash
uv run python -m repo_mirror_kit
```

## Development

```bash
# Lint
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/

# Type check
uv run mypy src/

# Tests
uv run pytest
```
