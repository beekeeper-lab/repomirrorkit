"""Tests for the tree-sitter foundation (BEAN-061)."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_mirror_kit.harvester.parsing import (
    language_for_path,
    parse_source,
    treesitter,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample-projects"


@pytest.mark.parametrize(
    ("path", "lang"),
    [
        ("a.ts", "typescript"),
        ("a.tsx", "tsx"),
        ("a.js", "javascript"),
        ("A.cs", "c_sharp"),
        ("a.py", None),
    ],
)
def test_language_for_path(path: str, lang: str | None) -> None:
    assert language_for_path(path) == lang


def test_parse_typescript_finds_exported_function() -> None:
    ps = parse_source(
        "route.ts", "export async function GET(req: Request) { return 1 }"
    )
    assert ps is not None
    funcs = ps.find_all("function_declaration")
    assert [ps.child_text(f, "name") for f in funcs] == ["GET"]
    assert ps.line_of(funcs[0]) == 1


def test_parse_tsx_with_jsx() -> None:
    ps = parse_source(
        "C.tsx", "export default function C(){ return <div className='x'/> }"
    )
    assert ps is not None
    assert ps.find_all("jsx_self_closing_element")


def test_parse_csharp_attribute() -> None:
    ps = parse_source("C.cs", '[HttpGet("items")] public class C { }')
    assert ps is not None
    assert ps.find_all("attribute")


def test_string_value() -> None:
    ps = parse_source("a.ts", "const x = '/api/users'")
    assert ps is not None
    (lit,) = ps.find_all("string")
    assert ps.string_value(lit) == "/api/users"


def test_unsupported_and_broken_inputs_degrade() -> None:
    assert parse_source("a.py", "x=1") is None
    ps = parse_source("a.ts", "export function (((")
    assert ps is not None  # tree-sitter is error tolerant
    assert ps.root.has_error


def test_missing_grammar_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    treesitter._parser_for.cache_clear()
    monkeypatch.setattr(treesitter, "_parser_for", lambda lang: None)
    assert parse_source("a.ts", "const x = 1") is None


def test_parses_all_fixture_js_ts_sources() -> None:
    files = [
        p for p in FIXTURES.rglob("*") if p.is_file() and language_for_path(p.name)
    ]
    assert files, "expected JS/TS fixtures"
    for path in files:
        ps = parse_source(path.name, path.read_bytes())
        assert ps is not None and not ps.root.has_error, path
