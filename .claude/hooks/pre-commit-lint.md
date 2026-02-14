# Hook Pack: Pre-Commit Lint

## Category
code-quality

## Purpose

Enforces code quality standards before every commit. Catches formatting, linting, import ordering, and type errors early so they never reach review or integration.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `format-check` | `pre-commit` | Run formatter in check mode (e.g. `ruff format --check`) | Zero formatting violations | Block commit; list files needing formatting |
| `lint-check` | `pre-commit` | Run linter on changed files (e.g. `ruff check`) | Zero error-severity findings | Block commit; list violations with locations |
| `import-sort` | `pre-commit` | Verify import ordering matches project convention | Imports sorted per configuration | Block commit; show expected order |
| `type-check` | `pre-commit` | Run type checker on changed files (e.g. `mypy --incremental`) | No new type errors introduced | Block commit; list type errors |

## Configuration

- **Default mode:** enforcing
- **Timeout:** 60 seconds per hook (type-check: 120 seconds)
- **Customization:** Projects can disable individual hooks via composition spec or `.foundry/hooks.yml`. For example, a prototype project might disable `type-check` while keeping the other three.

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | enforcing |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |

This pack is included at all posture levels because basic code quality is non-negotiable regardless of project criticality.
