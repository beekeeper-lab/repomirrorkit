"""Unit tests for the test pattern analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import TestPatternSurface
from repo_mirror_kit.harvester.analyzers.test_patterns import (
    _classify_test_type,
    _count_dotnet_tests,
    _count_go_tests,
    _count_js_tests,
    _count_python_tests,
    _count_ruby_minitest_tests,
    _count_ruby_rspec_tests,
    _detect_config_frameworks,
    _map_test_to_source_dotnet,
    _map_test_to_source_go,
    _map_test_to_source_js,
    _map_test_to_source_python,
    _map_test_to_source_ruby,
    analyze_test_patterns,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(
            path=p,
            size=100,
            extension=_ext(p),
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=100 * len(files),
        total_skipped=0,
    )


def _ext(path: str) -> str:
    """Extract file extension from a path."""
    dot = path.rfind(".")
    if dot == -1:
        return ""
    return path[dot:]


def _make_profile(stacks: dict[str, float] | None = None) -> StackProfile:
    """Build a StackProfile with given stacks."""
    return StackProfile(stacks=stacks or {}, evidence={}, signals=[])


def _write_file(workdir: Path, path: str, content: str) -> None:
    """Write a file relative to workdir."""
    full = workdir / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Jest/Vitest detection
# ---------------------------------------------------------------------------


class TestJestVitestDetection:
    """Tests for JavaScript/TypeScript test file detection."""

    def test_detects_test_ts_file(self) -> None:
        inventory = _make_inventory(["src/utils.test.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "jest"
        assert surfaces[0].test_file == "src/utils.test.ts"

    def test_detects_spec_tsx_file(self) -> None:
        inventory = _make_inventory(["src/Component.spec.tsx"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].test_file == "src/Component.spec.tsx"

    def test_detects_files_in_tests_dir(self) -> None:
        inventory = _make_inventory(["src/__tests__/helper.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].test_file == "src/__tests__/helper.ts"

    def test_vitest_config_detected(self) -> None:
        inventory = _make_inventory(["vitest.config.ts", "src/foo.test.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        test_surfaces = [s for s in surfaces if s.test_file == "src/foo.test.ts"]
        assert len(test_surfaces) == 1
        assert test_surfaces[0].framework == "vitest"

    def test_counts_it_and_test_blocks(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/foo.test.ts",
            """\
describe("foo", () => {
  it("should do something", () => {});
  it("should handle edge case", () => {});
  test("another test", () => {});
});
""",
        )
        count, names = _count_js_tests(tmp_path, "src/foo.test.ts")
        assert count == 3
        assert "foo" in names

    def test_skips_non_test_ts_files(self) -> None:
        inventory = _make_inventory(["src/utils.ts", "src/index.tsx"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 0

    def test_cypress_directory_detected_as_cypress(self) -> None:
        inventory = _make_inventory(["cypress/e2e/login.spec.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "cypress"
        assert surfaces[0].test_type == "e2e"

    def test_playwright_directory_detected(self) -> None:
        inventory = _make_inventory(["playwright.config.ts", "e2e/login.spec.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        test_surfaces = [s for s in surfaces if s.test_file == "e2e/login.spec.ts"]
        assert len(test_surfaces) == 1
        assert test_surfaces[0].framework == "playwright"
        assert test_surfaces[0].test_type == "e2e"


# ---------------------------------------------------------------------------
# Pytest detection
# ---------------------------------------------------------------------------


class TestPytestDetection:
    """Tests for Python test file detection."""

    def test_detects_test_prefix_file(self) -> None:
        inventory = _make_inventory(["tests/test_utils.py"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "pytest"
        assert surfaces[0].test_file == "tests/test_utils.py"

    def test_detects_test_suffix_file(self) -> None:
        inventory = _make_inventory(["tests/utils_test.py"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].test_file == "tests/utils_test.py"

    def test_detects_conftest(self) -> None:
        inventory = _make_inventory(["tests/conftest.py"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1

    def test_unittest_detected_from_content(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "tests/test_foo.py",
            "import unittest\nclass TestFoo(unittest.TestCase):\n    def test_bar(self): pass\n",
        )
        inventory = _make_inventory(["tests/test_foo.py"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile, tmp_path)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "unittest"

    def test_counts_python_test_functions(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "tests/test_foo.py",
            """\
def test_add():
    pass

def test_subtract():
    pass

async def test_async_op():
    pass

def helper():
    pass
""",
        )
        count, names = _count_python_tests(tmp_path, "tests/test_foo.py")
        assert count == 3
        assert "test_add" in names
        assert "test_subtract" in names
        assert "test_async_op" in names
        assert "helper" not in names

    def test_skips_non_test_python_files(self) -> None:
        inventory = _make_inventory(["src/utils.py", "src/main.py"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 0


# ---------------------------------------------------------------------------
# Go test detection
# ---------------------------------------------------------------------------


class TestGoDetection:
    """Tests for Go test file detection."""

    def test_detects_go_test_file(self) -> None:
        inventory = _make_inventory(["pkg/handler_test.go"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "go"
        assert surfaces[0].test_file == "pkg/handler_test.go"

    def test_counts_go_test_functions(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "pkg/handler_test.go",
            """\
package pkg

import "testing"

func TestAdd(t *testing.T) {}
func TestSubtract(t *testing.T) {}
func BenchmarkAdd(b *testing.B) {}
""",
        )
        count, names = _count_go_tests(tmp_path, "pkg/handler_test.go")
        assert count == 2
        assert "TestAdd" in names
        assert "TestSubtract" in names

    def test_maps_go_test_to_source(self) -> None:
        result = _map_test_to_source_go("pkg/handler_test.go")
        assert result == "pkg/handler.go"

    def test_skips_non_test_go_files(self) -> None:
        inventory = _make_inventory(["pkg/handler.go", "main.go"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 0


# ---------------------------------------------------------------------------
# .NET test detection
# ---------------------------------------------------------------------------


class TestDotnetDetection:
    """Tests for .NET test file detection."""

    def test_detects_xunit_test_file(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Tests/UserServiceTests.cs",
            """\
using Xunit;

public class UserServiceTests
{
    [Fact]
    public void GetUser_ReturnsUser() {}

    [Theory]
    public void GetUser_WithId_ReturnsCorrectUser() {}
}
""",
        )
        inventory = _make_inventory(["Tests/UserServiceTests.cs"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile, tmp_path)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "xunit"
        assert surfaces[0].test_count == 2

    def test_detects_nunit_test_file(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Tests/FooTest.cs",
            """\
using NUnit.Framework;

[TestFixture]
public class FooTest
{
    [Test]
    public void ShouldWork() {}
}
""",
        )
        inventory = _make_inventory(["Tests/FooTest.cs"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile, tmp_path)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "nunit"

    def test_detects_mstest_test_file(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Tests/BarTests.cs",
            """\
using Microsoft.VisualStudio.TestTools.UnitTesting;

[TestClass]
public class BarTests
{
    [TestMethod]
    public void ShouldDoThing() {}
}
""",
        )
        inventory = _make_inventory(["Tests/BarTests.cs"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile, tmp_path)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "mstest"

    def test_maps_dotnet_test_to_source(self) -> None:
        assert (
            _map_test_to_source_dotnet("Tests/UserServiceTests.cs")
            == "Tests/UserService.cs"
        )
        assert _map_test_to_source_dotnet("Tests/FooTest.cs") == "Tests/Foo.cs"


# ---------------------------------------------------------------------------
# Cypress/Playwright e2e detection
# ---------------------------------------------------------------------------


class TestE2EDetection:
    """Tests for E2E test framework detection."""

    def test_cypress_e2e_directory(self) -> None:
        inventory = _make_inventory(["cypress/e2e/login.spec.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].framework == "cypress"
        assert surfaces[0].test_type == "e2e"

    def test_playwright_e2e_directory(self) -> None:
        inventory = _make_inventory(["playwright.config.ts", "e2e/checkout.spec.ts"])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        test_surfaces = [s for s in surfaces if s.test_file == "e2e/checkout.spec.ts"]
        assert len(test_surfaces) == 1
        assert test_surfaces[0].framework == "playwright"
        assert test_surfaces[0].test_type == "e2e"


# ---------------------------------------------------------------------------
# Test type classification
# ---------------------------------------------------------------------------


class TestClassification:
    """Tests for test type classification."""

    def test_unit_by_default(self) -> None:
        result = _classify_test_type(
            "tests/test_foo.py", ("tests", "test_foo.py"), "pytest"
        )
        assert result == "unit"

    def test_integration_from_path(self) -> None:
        result = _classify_test_type(
            "tests/integration/test_db.py",
            ("tests", "integration", "test_db.py"),
            "pytest",
        )
        assert result == "integration"

    def test_e2e_from_framework(self) -> None:
        result = _classify_test_type(
            "cypress/e2e/login.spec.ts", ("cypress", "e2e", "login.spec.ts"), "cypress"
        )
        assert result == "e2e"

    def test_e2e_from_directory(self) -> None:
        result = _classify_test_type(
            "e2e/login.test.ts", ("e2e", "login.test.ts"), "jest"
        )
        assert result == "e2e"

    def test_snapshot_from_directory(self) -> None:
        result = _classify_test_type(
            "src/__snapshots__/App.test.ts.snap",
            ("src", "__snapshots__", "App.test.ts.snap"),
            "jest",
        )
        assert result == "snapshot"

    def test_performance_from_directory(self) -> None:
        result = _classify_test_type(
            "tests/performance/test_load.py",
            ("tests", "performance", "test_load.py"),
            "pytest",
        )
        assert result == "performance"


# ---------------------------------------------------------------------------
# Test-to-source mapping
# ---------------------------------------------------------------------------


class TestSourceMapping:
    """Tests for test-to-source file mapping."""

    def test_js_test_to_source(self) -> None:
        assert _map_test_to_source_js("src/utils.test.ts") == "src/utils.ts"

    def test_js_spec_to_source(self) -> None:
        assert _map_test_to_source_js("src/App.spec.tsx") == "src/App.tsx"

    def test_js_tests_dir_to_parent(self) -> None:
        result = _map_test_to_source_js("src/__tests__/utils.test.ts")
        assert result == "src/utils.ts"

    def test_python_test_prefix_to_source(self) -> None:
        result = _map_test_to_source_python("tests/test_utils.py")
        assert result == "src/utils.py"

    def test_python_test_suffix_to_source(self) -> None:
        result = _map_test_to_source_python("tests/utils_test.py")
        assert result == "src/utils.py"

    def test_python_conftest_returns_empty(self) -> None:
        result = _map_test_to_source_python("tests/conftest.py")
        assert result == ""

    def test_go_test_to_source(self) -> None:
        assert _map_test_to_source_go("pkg/handler_test.go") == "pkg/handler.go"

    def test_dotnet_tests_suffix(self) -> None:
        assert _map_test_to_source_dotnet("Tests/FooTests.cs") == "Tests/Foo.cs"

    def test_dotnet_test_suffix(self) -> None:
        assert _map_test_to_source_dotnet("Tests/FooTest.cs") == "Tests/Foo.cs"

    def test_ruby_rspec_to_source(self) -> None:
        result = _map_test_to_source_ruby("spec/models/user_spec.rb", "rspec")
        assert result == "lib/models/user.rb"

    def test_ruby_minitest_to_source(self) -> None:
        result = _map_test_to_source_ruby("test/models/user_test.rb", "minitest")
        assert result == "lib/models/user.rb"


# ---------------------------------------------------------------------------
# Config framework detection
# ---------------------------------------------------------------------------


class TestConfigDetection:
    """Tests for test config file detection."""

    def test_detects_jest_config(self) -> None:
        inventory = _make_inventory(["jest.config.ts"])
        frameworks = _detect_config_frameworks(inventory)
        assert "jest" in frameworks

    def test_detects_vitest_config(self) -> None:
        inventory = _make_inventory(["vitest.config.ts"])
        frameworks = _detect_config_frameworks(inventory)
        assert "vitest" in frameworks

    def test_detects_pytest_ini(self) -> None:
        inventory = _make_inventory(["pytest.ini"])
        frameworks = _detect_config_frameworks(inventory)
        assert "pytest" in frameworks

    def test_detects_playwright_config(self) -> None:
        inventory = _make_inventory(["playwright.config.ts"])
        frameworks = _detect_config_frameworks(inventory)
        assert "playwright" in frameworks

    def test_detects_cypress_config(self) -> None:
        inventory = _make_inventory(["cypress.config.ts"])
        frameworks = _detect_config_frameworks(inventory)
        assert "cypress" in frameworks

    def test_detects_mocharc(self) -> None:
        inventory = _make_inventory([".mocharc.yml"])
        frameworks = _detect_config_frameworks(inventory)
        assert "mocha" in frameworks

    def test_detects_rspec_config(self) -> None:
        inventory = _make_inventory([".rspec"])
        frameworks = _detect_config_frameworks(inventory)
        assert "rspec" in frameworks


# ---------------------------------------------------------------------------
# Test counting
# ---------------------------------------------------------------------------


class TestCounting:
    """Tests for test counting across ecosystems."""

    def test_counts_python_tests(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "test_foo.py",
            "def test_a(): pass\ndef test_b(): pass\ndef helper(): pass\n",
        )
        count, names = _count_python_tests(tmp_path, "test_foo.py")
        assert count == 2
        assert set(names) == {"test_a", "test_b"}

    def test_counts_go_tests(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "foo_test.go",
            'package foo\nimport "testing"\nfunc TestA(t *testing.T) {}\nfunc TestB(t *testing.T) {}\n',
        )
        count, _names = _count_go_tests(tmp_path, "foo_test.go")
        assert count == 2

    def test_counts_dotnet_tests(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "FooTests.cs",
            "[Fact]\npublic void TestA() {}\n[Theory]\npublic void TestB() {}\n",
        )
        count, _names = _count_dotnet_tests(tmp_path, "FooTests.cs")
        assert count == 2

    def test_counts_rspec_tests(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "foo_spec.rb",
            'it "does something" do\nend\nit "does another" do\nend\n',
        )
        count, _names = _count_ruby_rspec_tests(tmp_path, "foo_spec.rb")
        assert count == 2

    def test_counts_minitest_tests(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "foo_test.rb",
            "def test_something\nend\ndef test_other\nend\n",
        )
        count, _names = _count_ruby_minitest_tests(tmp_path, "foo_test.rb")
        assert count == 2

    def test_returns_zero_when_no_workdir(self) -> None:
        count, names = _count_python_tests(None, "test_foo.py")
        assert count == 0
        assert names == []


# ---------------------------------------------------------------------------
# TestPatternSurface dataclass
# ---------------------------------------------------------------------------


class TestTestPatternSurface:
    """Tests for the TestPatternSurface dataclass."""

    def test_surface_type_set(self) -> None:
        surface = TestPatternSurface(name="test")
        assert surface.surface_type == "test_pattern"

    def test_to_dict(self) -> None:
        surface = TestPatternSurface(
            name="jest:App.test.tsx",
            test_type="unit",
            framework="jest",
            test_file="src/App.test.tsx",
            subject_file="src/App.tsx",
            test_count=5,
            test_names=["renders", "handles click"],
        )
        d = surface.to_dict()
        assert d["surface_type"] == "test_pattern"
        assert d["test_type"] == "unit"
        assert d["framework"] == "jest"
        assert d["test_file"] == "src/App.test.tsx"
        assert d["subject_file"] == "src/App.tsx"
        assert d["test_count"] == 5
        assert d["test_names"] == ["renders", "handles click"]


# ---------------------------------------------------------------------------
# Full integration-style test
# ---------------------------------------------------------------------------


class TestAnalyzeTestPatternsIntegration:
    """Integration tests for analyze_test_patterns."""

    def test_mixed_ecosystem(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "src/utils.test.ts", 'it("works", () => {});\n')
        _write_file(tmp_path, "tests/test_main.py", "def test_main(): pass\n")
        _write_file(
            tmp_path,
            "pkg/handler_test.go",
            'package pkg\nimport "testing"\nfunc TestHandler(t *testing.T) {}\n',
        )

        inventory = _make_inventory(
            [
                "src/utils.test.ts",
                "tests/test_main.py",
                "pkg/handler_test.go",
            ]
        )
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile, tmp_path)

        assert len(surfaces) == 3
        frameworks = {s.framework for s in surfaces}
        assert "jest" in frameworks
        assert "pytest" in frameworks
        assert "go" in frameworks

    def test_empty_inventory(self) -> None:
        inventory = _make_inventory([])
        profile = _make_profile()
        surfaces = analyze_test_patterns(inventory, profile)
        assert surfaces == []
