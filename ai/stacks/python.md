# Python Stack Conventions

These conventions are non-negotiable defaults for Python projects in this team.
Deviations require an ADR with justification. "I prefer it differently" is not
justification.

---

## Defaults

| Concern              | Default Tool / Approach          |
|----------------------|----------------------------------|
| Python version       | 3.12+ (pin in `.python-version`) |
| Package manager      | `uv`                             |
| Build backend        | `hatchling`                      |
| Formatter / Linter   | `ruff` (replaces black, isort, flake8) |
| Type checker         | `mypy` (strict mode)             |
| Test framework       | `pytest`                         |
| Logging              | `structlog` (structured JSON)    |
| Docstring style      | Google-style                     |
| Layout               | `src/` layout                    |

---

## 1. Project Structure

```
project-root/
  src/
    <package_name>/
      __init__.py
      main.py              # Entry point (CLI or app factory)
      config.py             # Configuration loading, env var mapping
      models/               # Domain models and data classes
      services/             # Business logic (stateless functions/classes)
      repositories/         # Data access layer
      api/                  # HTTP handlers (FastAPI routers, Flask blueprints)
      utils/                # Pure utility functions (no business logic)
  tests/
    unit/                   # Mirror src/ structure
    integration/            # Tests requiring external resources
    conftest.py             # Shared fixtures
  pyproject.toml            # Single source of project metadata
  README.md
  .python-version           # Pin the Python minor version (e.g., 3.12)
```

**Rules:**
- Use `src/` layout. Flat layout causes import ambiguity.
- One package per repository. Monorepos use a `packages/` directory with
  independent `pyproject.toml` files.
- No code in `__init__.py` beyond public API re-exports.

---

## 2. Naming Conventions

| Element          | Convention       | Example                     |
|------------------|------------------|-----------------------------|
| Packages         | `snake_case`     | `order_processing`          |
| Modules          | `snake_case`     | `payment_gateway.py`        |
| Classes          | `PascalCase`     | `OrderProcessor`            |
| Functions        | `snake_case`     | `calculate_total`           |
| Constants        | `UPPER_SNAKE`    | `MAX_RETRY_COUNT`           |
| Private members  | `_leading_underscore` | `_validate_input`      |
| Type variables   | `PascalCase` + T suffix | `ItemT`, `ResponseT` |

Do not use double leading underscores (name mangling) unless you have a
specific, documented reason. It almost never helps.

---

## 3. Formatting and Linting

**Tool: Ruff** (replaces black, isort, flake8, and most pylint rules).

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "RUF"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
```

**Rules:**
- Ruff format is the only formatter. Do not also run Black.
- Format on save in your editor. CI rejects unformatted code.
- No `# noqa` comments without a justification comment on the same line.

---

## 4. Type Hints

**Policy: Mandatory on all public interfaces. Strongly encouraged internally.**

- All function signatures (parameters and return types) must have type hints.
- Use `from __future__ import annotations` at the top of every module for
  PEP 604 union syntax (`X | None` instead of `Optional[X]`).
- Use `typing.TypeAlias` for complex types referenced in multiple places.
- Run `mypy` in strict mode in CI.

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
```

Avoid `Any` except at system boundaries (e.g., deserializing unknown JSON).
Every `Any` must have a comment explaining why a precise type is not possible.

---

## 5. Import Ordering

Ruff handles this automatically with the `I` rule set. The order is:

1. Standard library imports
2. Third-party imports
3. Local application imports

Separate each group with a blank line. Use absolute imports. Relative imports
are allowed only within the same package for internal modules.

---

## 6. Docstring Style

**Style: Google-style docstrings.**

```python
def process_order(order_id: str, dry_run: bool = False) -> OrderResult:
    """Process a pending order and return the result.

    Validates the order, charges the payment method, and updates inventory.
    If dry_run is True, validates without side effects.

    Args:
        order_id: The unique identifier of the order to process.
        dry_run: If True, simulate processing without committing changes.

    Returns:
        An OrderResult containing the processing outcome and any warnings.

    Raises:
        OrderNotFoundError: If no order exists with the given ID.
        PaymentDeclinedError: If the payment method is declined.
    """
```

**Rules:**
- Every public function, class, and module has a docstring.
- First line is a single imperative sentence (not "This function does...").
- Document `Raises` only for exceptions the caller should handle, not internal
  implementation errors.

---

## 7. Virtual Environment and Dependency Management

**Tool: uv** (fast, reliable, replaces pip + venv + pip-tools).

```bash
# Create environment
uv venv

# Install dependencies
uv pip install -e ".[dev]"

# Add a dependency
uv pip install <package>  # then add to pyproject.toml

# Lock dependencies
uv pip compile pyproject.toml -o requirements.lock
```

**Rules:**
- All dependencies declared in `pyproject.toml` under `[project.dependencies]`.
- Dev dependencies under `[project.optional-dependencies] dev = [...]`.
- Commit `requirements.lock` for applications. Libraries do not commit lock
  files.
- Pin Python version in `.python-version`. CI and local dev must match.
- Never install packages globally. Always use a virtual environment.

---

## 8. Logging Conventions

**Use `structlog` for structured logging. Do not use `print()` for operational
output.**

```python
import structlog

logger = structlog.get_logger()

# Good: structured, context-rich
logger.info("order_processed", order_id=order_id, total=total, duration_ms=elapsed)

# Bad: unstructured string formatting
logger.info(f"Processed order {order_id} for ${total}")
```

**Rules:**
- Log levels: `debug` for developer diagnostics, `info` for operational events,
  `warning` for recoverable problems, `error` for failures requiring attention.
- Every log entry includes a static event name (snake_case) as the first
  argument, with variable data as keyword arguments.
- Never log secrets, tokens, passwords, or full PII. Log redacted identifiers.
- Configure JSON output in production, human-readable output in development.
- Include a correlation/request ID in all log entries for distributed tracing.

---

## 9. Error Handling

- Define application-specific exception classes inheriting from a project base
  exception (e.g., `class AppError(Exception)`).
- Catch specific exceptions, never bare `except:` or `except Exception:` at
  the function level.
- Let unexpected exceptions propagate to a top-level handler that logs them
  and returns a generic error response.
- Use `raise ... from err` to preserve exception chains.

---

## 10. Testing

**Framework: pytest.**

- Test file naming: `test_<module_name>.py`, mirroring `src/` structure.
- Use fixtures over setup/teardown methods.
- Aim for 80% line coverage minimum; measure branch coverage as the real
  metric.
- Mark slow tests with `@pytest.mark.slow` so they can be excluded in fast
  feedback loops.
- Integration tests use real databases/services in containers (testcontainers
  or docker-compose), never mocked storage.

---

## Do / Don't

**Do:**
- Use `src/` layout for every project without exception.
- Type-hint every public function signature (params + return).
- Use `structlog` with static event names and keyword arguments.
- Run `ruff check` and `ruff format` in CI as a gate.
- Use `raise ... from err` to preserve exception chains.
- Pin your Python minor version in `.python-version`.
- Write Google-style docstrings on all public APIs.

**Don't:**
- Run Black alongside Ruff -- Ruff's formatter replaces it entirely.
- Use `print()` for operational output; use `structlog`.
- Add bare `except:` or `except Exception:` at the function level.
- Use double-underscore name mangling without a documented reason.
- Commit code with unexplained `# noqa` or `# type: ignore` comments.
- Install packages globally -- always use a virtual environment.
- Use `Optional[X]` -- prefer `X | None` with `from __future__ import annotations`.

---

## Common Pitfalls

1. **Flat layout instead of `src/` layout.** Flat layout lets tests accidentally
   import the local package directory instead of the installed package, masking
   import errors that only surface in production.

2. **Forgetting `from __future__ import annotations`.** Without it, `X | None`
   syntax fails on Python < 3.10 and `TypeAlias` forward references break.
   Put it in every module as muscle memory.

3. **Logging with f-strings.** `logger.info(f"order {oid}")` defeats structured
   logging. The event name becomes unique per call, making log aggregation
   impossible. Always use keyword arguments.

4. **Bare `except Exception` in service code.** This swallows bugs silently.
   Catch the specific exceptions you know how to handle; let everything else
   propagate to the top-level error handler.

5. **Mixing ruff and black.** They fight over formatting. Ruff's formatter is a
   drop-in Black replacement. Pick one; it is Ruff.

6. **Not committing `requirements.lock` for applications.** Without a lock file,
   CI and production may resolve different dependency versions, causing
   "works on my machine" failures.

7. **Using `Any` without justification.** `Any` silently disables type checking
   for everything it touches. Every `Any` needs a comment explaining why a
   precise type is not possible.

---

## Checklist

- [ ] `src/` layout with `pyproject.toml` as the single metadata source
- [ ] `.python-version` file pinning the minor version (e.g., `3.12`)
- [ ] `ruff` configured in `pyproject.toml` with lint + format rules
- [ ] `mypy` in strict mode, zero errors in CI
- [ ] `from __future__ import annotations` in every module
- [ ] All public functions have type hints and Google-style docstrings
- [ ] `structlog` configured (JSON in prod, human-readable in dev)
- [ ] No bare `except:` or unqualified `except Exception:`
- [ ] Application-specific exception hierarchy defined
- [ ] `uv venv` used for virtual environment; no global installs
- [ ] `requirements.lock` committed for applications
- [ ] `pytest` with 80%+ branch coverage gate in CI
- [ ] No unexplained `# noqa` or `# type: ignore` comments
- [ ] CI gate runs: `ruff check`, `ruff format --check`, `mypy`, `pytest`

