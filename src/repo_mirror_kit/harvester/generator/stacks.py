"""Stack convention file generator.

Generates language and framework-specific coding convention files based on
detected technology stacks and patterns found in the analyzed repository.
"""

from __future__ import annotations

from dataclasses import dataclass

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.detectors.base import StackProfile


@dataclass(frozen=True)
class GeneratedStack:
    """A generated stack convention file.

    Attributes:
        relative_path: Path relative to the output project folder root.
        content: Markdown content of the stack convention file.
    """

    relative_path: str
    content: str


def generate_stacks(
    profile: StackProfile,
    surfaces: SurfaceCollection,
) -> list[GeneratedStack]:
    """Generate stack convention files from detected stacks.

    Args:
        profile: Detected technology stack profile.
        surfaces: All extracted surfaces.

    Returns:
        List of GeneratedStack instances ready to write.
    """
    results: list[GeneratedStack] = []
    stacks = set(profile.stacks.keys())

    if stacks & {"python", "fastapi", "flask", "django"}:
        results.append(_generate_python_stack(stacks, surfaces))

    if stacks & {"react", "nextjs", "vue", "svelte", "javascript", "typescript"}:
        results.append(_generate_js_ts_stack(stacks, surfaces))

    if stacks & {"dotnet", "csharp", "aspnet"}:
        results.append(_generate_dotnet_stack(stacks, surfaces))

    if stacks & {"go", "golang"}:
        results.append(_generate_go_stack(stacks, surfaces))

    if stacks & {"ruby", "rails"}:
        results.append(_generate_ruby_stack(stacks, surfaces))

    # If nothing matched, generate a generic conventions file
    if not results:
        results.append(_generate_generic_stack(stacks, surfaces))

    return results


def _generate_python_stack(
    stacks: set[str],
    surfaces: SurfaceCollection,
) -> GeneratedStack:
    """Generate Python stack conventions."""
    framework = "unknown"
    if "fastapi" in stacks:
        framework = "FastAPI"
    elif "flask" in stacks:
        framework = "Flask"
    elif "django" in stacks:
        framework = "Django"

    test_fw = _detect_python_test_framework(surfaces)
    pkg_mgr = _detect_python_package_manager(surfaces)

    content = f"""# Python Stack Conventions

## Language & Runtime

| Concern | Default |
|---------|---------|
| Python version | 3.12+ |
| Framework | {framework} |
| Package manager | {pkg_mgr} |
| Test framework | {test_fw} |
| Formatter / Linter | ruff |
| Type checker | mypy (strict mode) |
| Docstring style | Google-style |
| Layout | src/ layout |

## Coding Standards

- Use type hints on all public functions and methods.
- Use `from __future__ import annotations` for modern annotation syntax.
- Prefer dataclasses or Pydantic models over plain dicts.
- Use `pathlib.Path` over `os.path`.
- Use f-strings for string formatting.
- Use `raise ... from err` to preserve exception chains.
- No bare `except:` — always catch specific exceptions.

## Testing

- Place tests in `tests/` directory mirroring `src/` structure.
- Use `pytest` fixtures for shared setup.
- Name test files `test_<module>.py`.
- Name test functions `test_<behavior>`.
- Target 80%+ code coverage.

## Project Structure

```
src/<package_name>/
    __init__.py
    ...
tests/
    unit/
    integration/
pyproject.toml
```
"""
    return GeneratedStack(relative_path="ai/stacks/python.md", content=content)


def _detect_python_test_framework(surfaces: SurfaceCollection) -> str:
    """Detect Python test framework from test pattern surfaces."""
    for tp in surfaces.test_patterns:
        if tp.framework in ("pytest", "unittest"):
            return tp.framework
    return "pytest"


def _detect_python_package_manager(surfaces: SurfaceCollection) -> str:
    """Detect Python package manager from dependency surfaces."""
    for dep in surfaces.dependencies:
        if "pyproject.toml" in dep.manifest_file:
            return "uv / pip"
        if "requirements.txt" in dep.manifest_file:
            return "pip"
    return "pip"


def _generate_js_ts_stack(
    stacks: set[str],
    surfaces: SurfaceCollection,
) -> GeneratedStack:
    """Generate JavaScript/TypeScript stack conventions."""
    lang = "TypeScript" if "typescript" in stacks else "JavaScript"
    framework = "unknown"
    if "nextjs" in stacks:
        framework = "Next.js"
    elif "react" in stacks:
        framework = "React"
    elif "vue" in stacks:
        framework = "Vue"
    elif "svelte" in stacks:
        framework = "Svelte"

    test_fw = _detect_js_test_framework(surfaces)

    content = f"""# {lang} Stack Conventions

## Language & Runtime

| Concern | Default |
|---------|---------|
| Language | {lang} |
| Framework | {framework} |
| Test framework | {test_fw} |
| Package manager | npm / yarn |
| Linter | ESLint |
| Formatter | Prettier |

## Coding Standards

- Use strict TypeScript (`strict: true` in tsconfig) if using TypeScript.
- Prefer `const` over `let`; avoid `var`.
- Use async/await over raw Promises where possible.
- Use named exports over default exports.
- Components should be functional (hooks-based if React).

## Testing

- Place tests adjacent to source files or in `__tests__/` directories.
- Name test files `*.test.ts` or `*.spec.ts`.
- Use descriptive `describe`/`it` blocks.
- Mock external dependencies; don't mock internal modules.

## Project Structure

```
src/
    components/
    pages/ or app/
    lib/ or utils/
    types/
tests/ or __tests__/
package.json
tsconfig.json
```
"""
    return GeneratedStack(
        relative_path=f"ai/stacks/{lang.lower().replace(' ', '-')}.md",
        content=content,
    )


def _detect_js_test_framework(surfaces: SurfaceCollection) -> str:
    """Detect JS test framework from test pattern surfaces."""
    for tp in surfaces.test_patterns:
        if tp.framework in ("jest", "vitest", "mocha", "cypress", "playwright"):
            return tp.framework
    return "jest"


def _generate_dotnet_stack(
    stacks: set[str],
    surfaces: SurfaceCollection,
) -> GeneratedStack:
    """Generate .NET stack conventions."""
    test_fw = "xUnit"
    for tp in surfaces.test_patterns:
        if tp.framework in ("xunit", "nunit", "mstest"):
            test_fw = tp.framework
            break

    content = f"""# .NET Stack Conventions

## Language & Runtime

| Concern | Default |
|---------|---------|
| Language | C# |
| Framework | ASP.NET Core |
| Test framework | {test_fw} |
| Package manager | NuGet |

## Coding Standards

- Follow Microsoft C# coding conventions.
- Use nullable reference types (`<Nullable>enable</Nullable>`).
- Use dependency injection via built-in DI container.
- Use async/await for I/O-bound operations.
- Prefer records for immutable data transfer objects.

## Testing

- Place tests in a separate `*.Tests` project.
- Name test classes `<ClassUnderTest>Tests`.
- Use `[Fact]` for simple tests, `[Theory]` for parameterized.
- Use Moq or NSubstitute for mocking.

## Project Structure

```
src/
    <Project>/
        Controllers/
        Services/
        Models/
tests/
    <Project>.Tests/
<Solution>.sln
```
"""
    return GeneratedStack(relative_path="ai/stacks/dotnet.md", content=content)


def _generate_go_stack(
    stacks: set[str],
    surfaces: SurfaceCollection,
) -> GeneratedStack:
    """Generate Go stack conventions."""
    content = """# Go Stack Conventions

## Language & Runtime

| Concern | Default |
|---------|---------|
| Language | Go |
| Module system | Go modules |
| Test framework | testing (stdlib) |
| Linter | golangci-lint |

## Coding Standards

- Follow Effective Go and Go Code Review Comments.
- Use `gofmt` / `goimports` for formatting.
- Return errors, don't panic.
- Use table-driven tests.
- Keep packages small and focused.

## Testing

- Place tests in the same package as the code under test.
- Name test files `*_test.go`.
- Name test functions `Test<FunctionName>`.
- Use `testify` for assertions if adopted by the project.

## Project Structure

```
cmd/
    <app>/
        main.go
internal/
    <package>/
pkg/
    <package>/
go.mod
go.sum
```
"""
    return GeneratedStack(relative_path="ai/stacks/go.md", content=content)


def _generate_ruby_stack(
    stacks: set[str],
    surfaces: SurfaceCollection,
) -> GeneratedStack:
    """Generate Ruby stack conventions."""
    framework = "Rails" if "rails" in stacks else "Ruby"
    test_fw = "RSpec"
    for tp in surfaces.test_patterns:
        if tp.framework in ("rspec", "minitest"):
            test_fw = tp.framework
            break

    content = f"""# Ruby Stack Conventions

## Language & Runtime

| Concern | Default |
|---------|---------|
| Language | Ruby |
| Framework | {framework} |
| Test framework | {test_fw} |
| Package manager | Bundler |

## Coding Standards

- Follow the Ruby Style Guide.
- Use frozen_string_literal magic comment.
- Prefer keyword arguments for methods with 3+ parameters.
- Use guard clauses to reduce nesting.

## Testing

- Place specs in `spec/` directory mirroring `app/` or `lib/`.
- Name spec files `*_spec.rb`.
- Use `let` and `subject` for shared setup.
- Use factories over fixtures.

## Project Structure

```
app/
    controllers/
    models/
    views/
spec/
    models/
    requests/
Gemfile
```
"""
    return GeneratedStack(relative_path="ai/stacks/ruby.md", content=content)


def _generate_generic_stack(
    stacks: set[str],
    surfaces: SurfaceCollection,
) -> GeneratedStack:
    """Generate generic conventions when no specific language matched."""
    stack_list = ", ".join(sorted(stacks)) if stacks else "none detected"
    content = f"""# Stack Conventions

## Detected Technologies

{stack_list}

## General Coding Standards

- Write clean, readable code with consistent formatting.
- Use the project's established patterns and conventions.
- Add type annotations where the language supports them.
- Handle errors explicitly — no silent failures.
- Write tests for all new functionality.

## Testing

- Maintain test coverage for critical paths.
- Use descriptive test names that explain expected behavior.
- Mock external dependencies in unit tests.
"""
    return GeneratedStack(relative_path="ai/stacks/conventions.md", content=content)
