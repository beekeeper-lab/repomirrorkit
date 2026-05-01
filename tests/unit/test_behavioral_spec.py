"""Tests for the behavioral-spec post-pass analyzer (BEAN-054)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from repo_mirror_kit.harvester.analyzers.behavioral_spec import (
    _clean_jsdoc_body,
    _jsdoc_above,
    _python_docstring_at,
    _python_test_names,
    _test_names_for_surface,
    analyze_behavioral_spec,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile


def _fake_inventory(*paths: str) -> SimpleNamespace:
    """Minimal stand-in for InventoryResult — the analyzer only reads
    ``entries`` (list of strings)."""
    return SimpleNamespace(entries=list(paths))


# ---------------------------------------------------------------------------
# Python AST docstring extraction
# ---------------------------------------------------------------------------


class TestPythonDocstringExtraction:
    def test_picks_function_docstring_at_line(self, tmp_path: Path) -> None:
        src = tmp_path / "app.py"
        src.write_text(
            '''
def list_users():
    """Return all users as JSON."""
    return []


def create_user():
    """Create a new user from request body."""
    return {}
'''
        )
        from ast import parse

        tree = parse(src.read_text())
        # Line 3 is the docstring of list_users; line 8 is create_user's.
        assert (
            _python_docstring_at(tree, SourceRef(file_path="app.py", start_line=3))
            == "Return all users as JSON."
        )
        assert (
            _python_docstring_at(tree, SourceRef(file_path="app.py", start_line=8))
            == "Create a new user from request body."
        )

    def test_falls_back_to_module_docstring(self, tmp_path: Path) -> None:
        src = tmp_path / "app.py"
        src.write_text('"""Module-level summary."""\n\nx = 1\n')
        from ast import parse

        tree = parse(src.read_text())
        assert (
            _python_docstring_at(tree, SourceRef(file_path="app.py", start_line=3))
            == "Module-level summary."
        )

    def test_returns_none_when_no_docstring(self, tmp_path: Path) -> None:
        from ast import parse

        tree = parse("def foo():\n    return 1\n")
        result = _python_docstring_at(tree, SourceRef(file_path="x.py", start_line=1))
        assert result is None

    def test_picks_class_docstring(self, tmp_path: Path) -> None:
        from ast import parse

        tree = parse('class User:\n    """Persistent user record."""\n    pass\n')
        assert (
            _python_docstring_at(tree, SourceRef(file_path="x.py", start_line=2))
            == "Persistent user record."
        )


# ---------------------------------------------------------------------------
# JSDoc extraction
# ---------------------------------------------------------------------------


class TestJsdocExtraction:
    def test_extracts_simple_block(self) -> None:
        lines = [
            "/**",
            " * Lists every user.",
            " */",
            "export function listUsers() {}",
        ]
        result = _jsdoc_above(lines, target_line=4)
        assert result == "Lists every user."

    def test_extracts_multiline_block(self) -> None:
        lines = [
            "/**",
            " * Authenticate the user.",
            " *",
            " * @param token JWT bearer.",
            " */",
            "export function auth(token: string) {}",
        ]
        result = _jsdoc_above(lines, target_line=6)
        assert result is not None
        assert "Authenticate the user." in result
        assert "@param token JWT bearer." in result

    def test_skips_blank_lines_between_jsdoc_and_target(self) -> None:
        lines = [
            "/** Quick note. */",
            "",
            "",
            "function foo() {}",
        ]
        assert _jsdoc_above(lines, target_line=4) == "Quick note."

    def test_returns_none_with_no_jsdoc(self) -> None:
        lines = [
            "// regular comment",
            "function foo() {}",
        ]
        assert _jsdoc_above(lines, target_line=2) is None

    def test_clean_body_strips_star_markers(self) -> None:
        body = "\n * line one\n * line two\n "
        assert _clean_jsdoc_body(body) == "line one\nline two"


# ---------------------------------------------------------------------------
# Test-name harvesting
# ---------------------------------------------------------------------------


class TestPythonTestNames:
    def test_finds_test_functions(self) -> None:
        source = (
            "def helper(): pass\n"
            "def test_user_can_log_in(): pass\n"
            "def test_login_with_bad_password(): pass\n"
        )
        names = _python_test_names(source)
        assert names == ["test_user_can_log_in", "test_login_with_bad_password"]

    def test_skips_non_test_functions(self) -> None:
        names = _python_test_names("def login(): pass\n")
        assert names == []

    def test_handles_async_test(self) -> None:
        names = _python_test_names("async def test_async_login(): pass\n")
        assert names == ["test_async_login"]

    def test_silent_on_syntax_error(self) -> None:
        # Malformed Python should not raise.
        assert _python_test_names("def def def!") == []


class TestTestNameMatching:
    def test_matches_substring_case_insensitive(self) -> None:
        corpus = [
            (Path("tests/test_user.py"), "test_user_can_log_in"),
            (Path("tests/test_user.py"), "test_user_can_log_out"),
            (Path("tests/test_other.py"), "test_unrelated"),
        ]
        result = _test_names_for_surface("User", corpus)
        assert "test_user_can_log_in" in result
        assert "test_user_can_log_out" in result
        assert "test_unrelated" not in result

    def test_matches_token_in_camel_or_snake(self) -> None:
        corpus = [
            (Path("x"), "test_create_user_with_email"),
        ]
        # Surface name "createUser" tokenizes to {create, user}; both appear
        # in the test name.
        result = _test_names_for_surface("createUser", corpus)
        assert "test_create_user_with_email" in result

    def test_skips_short_surface_names(self) -> None:
        corpus = [(Path("x"), "test_x_works")]
        # 1-char name should not match (too noisy).
        assert _test_names_for_surface("x", corpus) == []

    def test_caps_at_ten_matches(self) -> None:
        corpus = [(Path("x"), f"test_user_case_{i}") for i in range(20)]
        assert len(_test_names_for_surface("User", corpus)) == 10


# ---------------------------------------------------------------------------
# Top-level integration of the analyzer
# ---------------------------------------------------------------------------


class TestAnalyzeBehavioralSpec:
    def test_attaches_python_docstring_to_route(self, tmp_path: Path) -> None:
        # Source file with a docstring.
        (tmp_path / "app.py").write_text(
            "from flask import Flask\n"
            "app = Flask(__name__)\n"
            "\n"
            "\n"
            '@app.route("/api/users")\n'
            "def list_users():\n"
            '    """Return all users as JSON."""\n'
            "    return []\n"
        )
        coll = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="ListUsers",
                    path="/api/users",
                    method="GET",
                    source_refs=[SourceRef(file_path="app.py", start_line=6)],
                )
            ]
        )
        analyze_behavioral_spec(
            _fake_inventory(),
            StackProfile(),
            tmp_path,
            coll,
        )
        signals = coll.routes[0].enrichment.get("behavioral_signals")
        assert signals is not None
        assert signals["docstring"] == "Return all users as JSON."

    def test_attaches_jsdoc_to_api(self, tmp_path: Path) -> None:
        (tmp_path / "route.ts").write_text(
            "/**\n"
            " * Get the current user.\n"
            " */\n"
            "export async function GET() { return {} }\n"
        )
        coll = SurfaceCollection(
            apis=[
                ApiSurface(
                    name="GetUser",
                    method="GET",
                    path="/api/me",
                    source_refs=[SourceRef(file_path="route.ts", start_line=4)],
                )
            ]
        )
        analyze_behavioral_spec(
            _fake_inventory(),
            StackProfile(),
            tmp_path,
            coll,
        )
        signals = coll.apis[0].enrichment.get("behavioral_signals")
        assert signals is not None
        assert "Get the current user." in (signals["jsdoc"] or "")

    def test_attaches_matching_test_names(self, tmp_path: Path) -> None:
        # Test file in inventory with a matching test name.
        test_path = tmp_path / "tests" / "test_user.py"
        test_path.parent.mkdir()
        test_path.write_text(
            "def test_user_can_log_in(): pass\ndef test_unrelated(): pass\n"
        )
        coll = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="UserLogin",
                    path="/login",
                    method="POST",
                    source_refs=[],
                )
            ]
        )
        analyze_behavioral_spec(
            _fake_inventory("tests/test_user.py"),
            StackProfile(),
            tmp_path,
            coll,
        )
        signals = coll.routes[0].enrichment.get("behavioral_signals")
        assert signals is not None
        assert "test_user_can_log_in" in signals["test_names"]
        assert "test_unrelated" not in signals["test_names"]

    def test_does_not_clobber_existing_signals(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="X",
                    path="/x",
                    method="GET",
                    source_refs=[],
                    enrichment={"behavioral_signals": {"docstring": "preset"}},
                )
            ]
        )
        analyze_behavioral_spec(
            _fake_inventory(),
            StackProfile(),
            tmp_path,
            coll,
        )
        assert coll.routes[0].enrichment["behavioral_signals"] == {
            "docstring": "preset"
        }

    def test_no_signal_attached_when_nothing_matches(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="MysterySurface",
                    path="/x",
                    method="GET",
                    source_refs=[SourceRef(file_path="missing.py", start_line=1)],
                )
            ]
        )
        analyze_behavioral_spec(
            _fake_inventory(),
            StackProfile(),
            tmp_path,
            coll,
        )
        # No file, no test names → no signals attached.
        assert "behavioral_signals" not in coll.routes[0].enrichment

    def test_silent_on_unparsable_python(self, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text("def def def !!!\n")
        coll = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="X",
                    path="/x",
                    method="GET",
                    source_refs=[SourceRef(file_path="broken.py", start_line=1)],
                )
            ]
        )
        # Should not raise.
        analyze_behavioral_spec(
            _fake_inventory(),
            StackProfile(),
            tmp_path,
            coll,
        )
