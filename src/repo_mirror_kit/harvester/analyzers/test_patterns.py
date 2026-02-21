"""Test pattern analyzer for detecting test files, frameworks, and test structure.

Discovers test files across multiple ecosystems, identifies testing frameworks,
classifies tests by type (unit/integration/e2e/snapshot/performance), maps test
files to source files via naming conventions, and counts tests per file.

Supported ecosystems:
- JavaScript/TypeScript: Jest, Vitest, Mocha, Cypress, Playwright
- Python: pytest, unittest
- Go: testing package
- .NET: xUnit, NUnit, MSTest
- Ruby: RSpec, Minitest

Uses heuristic-based extraction (regex, not AST) per project conventions.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    SourceRef,
    TestPatternSurface,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

_MAX_FILE_READ_BYTES: int = 512_000  # 500 KB limit for heuristic scanning.

# ---------------------------------------------------------------------------
# Test file detection patterns
# ---------------------------------------------------------------------------

# JS/TS test file patterns
_JS_TS_TEST_RE = re.compile(r"(?:\.test|\.spec)\.[jt]sx?$")

# JS/TS test directories
_JS_TS_TEST_DIRS: frozenset[str] = frozenset({"__tests__", "__test__"})

# E2E directories (Cypress, Playwright)
_E2E_DIRS: frozenset[str] = frozenset({"cypress", "e2e", "playwright"})

# Python test file patterns
_PYTHON_TEST_RE = re.compile(r"(?:^test_.*\.py$|.*_test\.py$|^conftest\.py$)")

# Go test file pattern
_GO_TEST_RE = re.compile(r"_test\.go$")

# .NET test file patterns
_DOTNET_TEST_RE = re.compile(r"(?:Tests?\.cs$|Spec\.cs$)")

# .NET test project directories
_DOTNET_TEST_DIRS: frozenset[str] = frozenset(
    {"Tests", "Test", "UnitTests", "IntegrationTests"}
)

# Ruby test patterns
_RUBY_SPEC_RE = re.compile(r"_spec\.rb$")
_RUBY_TEST_RE = re.compile(r"_test\.rb$")

# ---------------------------------------------------------------------------
# Test counting patterns (regex-based, approximate)
# ---------------------------------------------------------------------------

# JS/TS: it("...", describe("...
_JS_IT_RE = re.compile(r"""(?:^|\s)it\s*\(\s*["'`]""", re.MULTILINE)
_JS_TEST_FN_RE = re.compile(r"""(?:^|\s)test\s*\(\s*["'`]""", re.MULTILINE)
_JS_DESCRIBE_RE = re.compile(
    r"""(?:^|\s)describe\s*\(\s*["'`]([^"'`]+)""", re.MULTILINE
)

# Python: def test_xxx
_PY_TEST_FN_RE = re.compile(r"^\s*(?:def|async\s+def)\s+(test_\w+)", re.MULTILINE)

# Go: func TestXxx
_GO_TEST_FN_RE = re.compile(r"^func\s+(Test\w+)", re.MULTILINE)

# .NET: [Test], [Fact], [Theory], [TestMethod]
_DOTNET_TEST_ATTR_RE = re.compile(
    r"^\s*\[(Test|Fact|Theory|TestMethod|TestCase)\]", re.MULTILINE
)

# Ruby RSpec: it "...", specify "..."
_RUBY_IT_RE = re.compile(r"""(?:^|\s)(?:it|specify)\s+["']([^"']+)""", re.MULTILINE)

# Ruby Minitest: def test_
_RUBY_TEST_FN_RE = re.compile(r"^\s*def\s+(test_\w+)", re.MULTILINE)

# ---------------------------------------------------------------------------
# Framework detection from config files
# ---------------------------------------------------------------------------

_TEST_CONFIG_FILES: dict[str, str] = {
    "jest.config.js": "jest",
    "jest.config.ts": "jest",
    "jest.config.mjs": "jest",
    "jest.config.cjs": "jest",
    "vitest.config.ts": "vitest",
    "vitest.config.js": "vitest",
    "vitest.config.mts": "vitest",
    "playwright.config.ts": "playwright",
    "playwright.config.js": "playwright",
    "cypress.config.ts": "cypress",
    "cypress.config.js": "cypress",
    "cypress.json": "cypress",
    ".mocharc.yml": "mocha",
    ".mocharc.yaml": "mocha",
    ".mocharc.json": "mocha",
    ".mocharc.js": "mocha",
    ".mocharc.cjs": "mocha",
    "pytest.ini": "pytest",
    "conftest.py": "pytest",
    "tox.ini": "pytest",
    ".rspec": "rspec",
}

# ---------------------------------------------------------------------------
# Test type classification
# ---------------------------------------------------------------------------

_INTEGRATION_INDICATORS: frozenset[str] = frozenset(
    {"integration", "integ", "api_test", "api-test", "db_test", "db-test"}
)

_E2E_INDICATORS: frozenset[str] = frozenset(
    {"e2e", "end-to-end", "end_to_end", "cypress", "playwright", "acceptance"}
)

_SNAPSHOT_INDICATORS: frozenset[str] = frozenset({"snapshot", "snap", "__snapshots__"})

_PERFORMANCE_INDICATORS: frozenset[str] = frozenset(
    {"perf", "performance", "benchmark", "bench", "load"}
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_test_patterns(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path | None = None,
) -> list[TestPatternSurface]:
    """Discover test files and extract test pattern surfaces.

    Examines the file inventory to find test files, determines the testing
    framework, classifies tests by type, maps to source files, and counts
    tests per file.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results identifying which stacks are present.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of ``TestPatternSurface`` objects, one per test file.
    """
    surfaces: list[TestPatternSurface] = []
    config_frameworks = _detect_config_frameworks(inventory)

    for entry in inventory.files:
        path_obj = PurePosixPath(entry.path)
        parts = path_obj.parts
        ext = entry.extension
        filename = path_obj.name

        # --- JavaScript/TypeScript tests ---
        if ext in {".js", ".jsx", ".ts", ".tsx"}:
            if _JS_TS_TEST_RE.search(filename) or _is_in_test_dir(
                parts, _JS_TS_TEST_DIRS
            ):
                framework = _detect_js_framework(entry.path, config_frameworks, parts)
                test_type = _classify_test_type(entry.path, parts, framework)
                subject = _map_test_to_source_js(entry.path)
                test_count, test_names = _count_js_tests(workdir, entry.path)

                surfaces.append(
                    TestPatternSurface(
                        name=f"{framework}:{filename}",
                        test_type=test_type,
                        framework=framework,
                        test_file=entry.path,
                        subject_file=subject,
                        test_count=test_count,
                        test_names=test_names,
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )
                continue

        # --- Python tests ---
        if ext == ".py":
            if _PYTHON_TEST_RE.search(filename):
                framework = _detect_python_framework(
                    workdir, entry.path, config_frameworks
                )
                test_type = _classify_test_type(entry.path, parts, framework)
                subject = _map_test_to_source_python(entry.path)
                test_count, test_names = _count_python_tests(workdir, entry.path)

                surfaces.append(
                    TestPatternSurface(
                        name=f"{framework}:{filename}",
                        test_type=test_type,
                        framework=framework,
                        test_file=entry.path,
                        subject_file=subject,
                        test_count=test_count,
                        test_names=test_names,
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )
                continue

        # --- Go tests ---
        if ext == ".go" and _GO_TEST_RE.search(filename):
            test_type = _classify_test_type(entry.path, parts, "go")
            subject = _map_test_to_source_go(entry.path)
            test_count, test_names = _count_go_tests(workdir, entry.path)

            surfaces.append(
                TestPatternSurface(
                    name=f"go:{filename}",
                    test_type=test_type,
                    framework="go",
                    test_file=entry.path,
                    subject_file=subject,
                    test_count=test_count,
                    test_names=test_names,
                    source_refs=[SourceRef(file_path=entry.path)],
                )
            )
            continue

        # --- .NET tests ---
        if ext == ".cs" and (
            _DOTNET_TEST_RE.search(filename)
            or _is_in_test_dir(parts, _DOTNET_TEST_DIRS)
        ):
            framework = _detect_dotnet_framework(workdir, entry.path)
            test_type = _classify_test_type(entry.path, parts, framework)
            subject = _map_test_to_source_dotnet(entry.path)
            test_count, test_names = _count_dotnet_tests(workdir, entry.path)

            if test_count > 0 or _DOTNET_TEST_RE.search(filename):
                surfaces.append(
                    TestPatternSurface(
                        name=f"{framework}:{filename}",
                        test_type=test_type,
                        framework=framework,
                        test_file=entry.path,
                        subject_file=subject,
                        test_count=test_count,
                        test_names=test_names,
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )
            continue

        # --- Ruby tests ---
        if ext == ".rb":
            if _RUBY_SPEC_RE.search(filename):
                test_type = _classify_test_type(entry.path, parts, "rspec")
                subject = _map_test_to_source_ruby(entry.path, "rspec")
                test_count, test_names = _count_ruby_rspec_tests(workdir, entry.path)

                surfaces.append(
                    TestPatternSurface(
                        name=f"rspec:{filename}",
                        test_type=test_type,
                        framework="rspec",
                        test_file=entry.path,
                        subject_file=subject,
                        test_count=test_count,
                        test_names=test_names,
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )
                continue

            if _RUBY_TEST_RE.search(filename):
                test_type = _classify_test_type(entry.path, parts, "minitest")
                subject = _map_test_to_source_ruby(entry.path, "minitest")
                test_count, test_names = _count_ruby_minitest_tests(workdir, entry.path)

                surfaces.append(
                    TestPatternSurface(
                        name=f"minitest:{filename}",
                        test_type=test_type,
                        framework="minitest",
                        test_file=entry.path,
                        subject_file=subject,
                        test_count=test_count,
                        test_names=test_names,
                        source_refs=[SourceRef(file_path=entry.path)],
                    )
                )
                continue

    logger.info("test_pattern_analysis_complete", total_test_files=len(surfaces))
    return surfaces


# ---------------------------------------------------------------------------
# Config framework detection
# ---------------------------------------------------------------------------


def _detect_config_frameworks(inventory: InventoryResult) -> set[str]:
    """Detect test frameworks from config files in the inventory."""
    frameworks: set[str] = set()
    for entry in inventory.files:
        filename = PurePosixPath(entry.path).name
        if filename in _TEST_CONFIG_FILES:
            frameworks.add(_TEST_CONFIG_FILES[filename])
    return frameworks


# ---------------------------------------------------------------------------
# Framework detection helpers
# ---------------------------------------------------------------------------


def _detect_js_framework(
    file_path: str,
    config_frameworks: set[str],
    parts: tuple[str, ...],
) -> str:
    """Detect JS/TS test framework from context."""
    # E2E frameworks take precedence based on directory
    lower_parts = {p.lower() for p in parts}
    if "cypress" in lower_parts:
        return "cypress"
    if "playwright" in lower_parts or "e2e" in lower_parts:
        if "playwright" in config_frameworks:
            return "playwright"

    # Check config-detected frameworks
    for fw in ("vitest", "jest", "mocha"):
        if fw in config_frameworks:
            return fw

    # Default heuristic: .test. files → jest, .spec. → vitest
    if ".spec." in file_path:
        return "vitest" if "vitest" in config_frameworks else "jest"
    return "jest"


def _detect_python_framework(
    workdir: Path | None,
    file_path: str,
    config_frameworks: set[str],
) -> str:
    """Detect Python test framework."""
    if "pytest" in config_frameworks:
        return "pytest"

    # Read file to check for unittest patterns
    content = _read_file_safe(workdir, file_path)
    if content and "unittest.TestCase" in content:
        return "unittest"

    return "pytest"


def _detect_dotnet_framework(
    workdir: Path | None,
    file_path: str,
) -> str:
    """Detect .NET test framework from test attributes."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return "xunit"

    if "[Fact]" in content or "[Theory]" in content:
        return "xunit"
    if "[Test]" in content or "[TestFixture]" in content:
        return "nunit"
    if "[TestMethod]" in content or "[TestClass]" in content:
        return "mstest"

    return "xunit"


# ---------------------------------------------------------------------------
# Test type classification
# ---------------------------------------------------------------------------


def _classify_test_type(
    file_path: str,
    parts: tuple[str, ...],
    framework: str,
) -> str:
    """Classify a test file as unit, integration, e2e, snapshot, or performance."""
    lower_path = file_path.lower()
    lower_parts = {p.lower() for p in parts}

    # E2E frameworks are always e2e
    if framework in {"cypress", "playwright"}:
        return "e2e"

    # Check path segments for indicators
    for indicator in _E2E_INDICATORS:
        if indicator in lower_parts or indicator in lower_path:
            return "e2e"

    for indicator in _SNAPSHOT_INDICATORS:
        if indicator in lower_parts or indicator in lower_path:
            return "snapshot"

    for indicator in _PERFORMANCE_INDICATORS:
        if indicator in lower_parts or indicator in lower_path:
            return "performance"

    for indicator in _INTEGRATION_INDICATORS:
        if indicator in lower_parts or indicator in lower_path:
            return "integration"

    return "unit"


# ---------------------------------------------------------------------------
# Test-to-source mapping
# ---------------------------------------------------------------------------


def _map_test_to_source_js(test_path: str) -> str:
    """Map a JS/TS test file to its likely source file.

    Naming conventions:
    - ``foo.test.ts`` → ``foo.ts``
    - ``foo.spec.tsx`` → ``foo.tsx``
    - ``__tests__/foo.test.ts`` → ``../foo.ts``
    """
    p = PurePosixPath(test_path)
    stem = p.stem  # e.g. "foo.test" from "foo.test.ts"
    ext = p.suffix  # e.g. ".ts"

    # Remove .test or .spec from the stem
    if stem.endswith(".test") or stem.endswith(".spec"):
        base_stem = stem.rsplit(".", 1)[0]
    else:
        base_stem = stem

    source_name = base_stem + ext

    # If in __tests__ directory, look one level up
    parent = p.parent
    if parent.name in _JS_TS_TEST_DIRS:
        return str(parent.parent / source_name)

    return str(parent / source_name)


def _map_test_to_source_python(test_path: str) -> str:
    """Map a Python test file to its likely source file.

    Naming conventions:
    - ``test_foo.py`` → ``foo.py``
    - ``foo_test.py`` → ``foo.py``
    - ``tests/test_foo.py`` → ``src/foo.py`` (heuristic)
    """
    p = PurePosixPath(test_path)
    stem = p.stem

    if stem == "conftest":
        return ""

    if stem.startswith("test_"):
        base = stem[5:]  # Remove "test_" prefix
    elif stem.endswith("_test"):
        base = stem[:-5]  # Remove "_test" suffix
    else:
        base = stem

    source_name = base + ".py"

    # Try to map tests/ → src/ if in a tests directory
    parent = p.parent
    parent_parts = list(parent.parts)
    for i, part in enumerate(parent_parts):
        if part in {"tests", "test"}:
            src_parts = [*parent_parts[:i], "src", *parent_parts[i + 1 :]]
            return (
                str(PurePosixPath(*src_parts) / source_name)
                if src_parts
                else source_name
            )

    return str(parent / source_name)


def _map_test_to_source_go(test_path: str) -> str:
    """Map a Go test file to its source file.

    ``foo_test.go`` → ``foo.go``
    """
    p = PurePosixPath(test_path)
    base = p.stem.removesuffix("_test")
    return str(p.parent / (base + ".go"))


def _map_test_to_source_dotnet(test_path: str) -> str:
    """Map a .NET test file to its likely source file.

    ``FooTests.cs`` → ``Foo.cs``
    ``FooTest.cs`` → ``Foo.cs``
    """
    p = PurePosixPath(test_path)
    stem = p.stem

    if stem.endswith("Tests"):
        base = stem[:-5]
    elif stem.endswith("Test"):
        base = stem[:-4]
    elif stem.endswith("Spec"):
        base = stem[:-4]
    else:
        base = stem

    return str(p.parent / (base + ".cs"))


def _map_test_to_source_ruby(test_path: str, framework: str) -> str:
    """Map a Ruby test file to its source file.

    - RSpec: ``foo_spec.rb`` → ``foo.rb``
    - Minitest: ``foo_test.rb`` → ``foo.rb``
    """
    p = PurePosixPath(test_path)
    stem = p.stem

    if framework == "rspec" and stem.endswith("_spec"):
        base = stem[:-5]
    elif framework == "minitest" and stem.endswith("_test"):
        base = stem[:-5]
    else:
        base = stem

    # Try to map spec/ → lib/ or app/
    parent = p.parent
    parent_parts = list(parent.parts)
    for i, part in enumerate(parent_parts):
        if part == "spec":
            lib_parts = [*parent_parts[:i], "lib", *parent_parts[i + 1 :]]
            return (
                str(PurePosixPath(*lib_parts) / (base + ".rb"))
                if lib_parts
                else base + ".rb"
            )
        if part == "test":
            lib_parts = [*parent_parts[:i], "lib", *parent_parts[i + 1 :]]
            return (
                str(PurePosixPath(*lib_parts) / (base + ".rb"))
                if lib_parts
                else base + ".rb"
            )

    return str(parent / (base + ".rb"))


# ---------------------------------------------------------------------------
# Test counting
# ---------------------------------------------------------------------------


def _count_js_tests(
    workdir: Path | None,
    file_path: str,
) -> tuple[int, list[str]]:
    """Count JS/TS tests in a file (it/test blocks)."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return 0, []

    names: list[str] = []
    count = 0

    for _match in _JS_IT_RE.finditer(content):
        count += 1
    for _match in _JS_TEST_FN_RE.finditer(content):
        count += 1

    # Extract describe block names for context
    for match in _JS_DESCRIBE_RE.finditer(content):
        names.append(match.group(1))

    return count, names


def _count_python_tests(
    workdir: Path | None,
    file_path: str,
) -> tuple[int, list[str]]:
    """Count Python test functions in a file."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return 0, []

    names: list[str] = []
    for match in _PY_TEST_FN_RE.finditer(content):
        names.append(match.group(1))

    return len(names), names


def _count_go_tests(
    workdir: Path | None,
    file_path: str,
) -> tuple[int, list[str]]:
    """Count Go test functions in a file."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return 0, []

    names: list[str] = []
    for match in _GO_TEST_FN_RE.finditer(content):
        names.append(match.group(1))

    return len(names), names


def _count_dotnet_tests(
    workdir: Path | None,
    file_path: str,
) -> tuple[int, list[str]]:
    """Count .NET test methods in a file."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return 0, []

    names: list[str] = []
    count = len(_DOTNET_TEST_ATTR_RE.findall(content))

    # Extract test method names following attributes
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if _DOTNET_TEST_ATTR_RE.search(line):
            # Look at the next non-empty line for the method name
            for j in range(i + 1, min(i + 3, len(lines))):
                method_match = re.search(
                    r"(?:public|private|protected)?\s*(?:async\s+)?(?:void|Task)\s+(\w+)",
                    lines[j],
                )
                if method_match:
                    names.append(method_match.group(1))
                    break

    return count, names


def _count_ruby_rspec_tests(
    workdir: Path | None,
    file_path: str,
) -> tuple[int, list[str]]:
    """Count Ruby RSpec examples in a file."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return 0, []

    names: list[str] = []
    for match in _RUBY_IT_RE.finditer(content):
        names.append(match.group(1))

    return len(names), names


def _count_ruby_minitest_tests(
    workdir: Path | None,
    file_path: str,
) -> tuple[int, list[str]]:
    """Count Ruby Minitest tests in a file."""
    content = _read_file_safe(workdir, file_path)
    if content is None:
        return 0, []

    names: list[str] = []
    for match in _RUBY_TEST_FN_RE.finditer(content):
        names.append(match.group(1))

    return len(names), names


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_in_test_dir(parts: tuple[str, ...], test_dirs: frozenset[str]) -> bool:
    """Check if any path segment matches a test directory name."""
    return bool(set(parts) & test_dirs)


def _read_file_safe(workdir: Path | None, file_path: str) -> str | None:
    """Read a file safely, returning None on failure."""
    if workdir is None:
        return None
    try:
        full_path = workdir / file_path
        content = full_path.read_text(encoding="utf-8")
        if len(content) > _MAX_FILE_READ_BYTES:
            logger.debug(
                "test_file_too_large",
                path=file_path,
                size=len(content),
            )
            return None
        return content
    except OSError:
        logger.debug("test_file_read_failed", path=file_path)
        return None
