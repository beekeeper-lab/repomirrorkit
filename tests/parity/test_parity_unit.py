"""Unit tests for the parity engine using a tiny in-process HTTP server."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from repo_mirror_kit.harvester.parity.gherkin_runner import (
    load_scenarios,
    parse_feature,
    run_scenarios,
)
from repo_mirror_kit.harvester.parity.goldens import (
    GOLDEN_VERSION,
    GoldenError,
    capture,
    replay,
)
from repo_mirror_kit.harvester.parity.schema_diff import diff_schemas
from repo_mirror_kit.harvester.parity.score import WEIGHTS, ParityReport


@contextmanager
def serve(routes: dict[tuple[str, str], tuple[int, Any]]) -> Iterator[str]:
    class H(BaseHTTPRequestHandler):
        def _go(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            status, body = routes.get(
                (self.command, self.path), (404, {"error": "nope"})
            )
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = _go  # noqa: N815

        def log_message(self, *a: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()


SCRIPT = {
    "name": "t",
    "requests": [
        {"name": "list", "method": "GET", "path": "/items"},
        {"name": "bad", "method": "POST", "path": "/items", "json": {"x": 1}},
    ],
}
ROUTES = {
    ("GET", "/items"): (200, [{"id": 1, "name": "a", "created": "t0"}]),
    ("POST", "/items"): (400, {"error": "name is required"}),
}


def test_capture_and_replay_roundtrip() -> None:
    with serve(ROUTES) as url:
        golden = capture(url, SCRIPT, {}, "unit", volatile_fields=("created",))
    assert golden["schema_version"] == GOLDEN_VERSION
    assert [i["response"]["status"] for i in golden["interactions"]] == [200, 400]
    with serve(ROUTES) as url:
        result = replay(url, golden)
    assert (
        result.pass_rate == 1.0
        and result.strict_rate == 1.0
        and result.field_match_rate == 1.0
    )


def test_volatile_and_message_tolerance_and_strictness() -> None:
    with serve(ROUTES) as url:
        golden = capture(url, SCRIPT, {}, "unit", volatile_fields=("created",))
    variant = {
        ("GET", "/items"): (200, [{"id": 1, "name": "a", "created": "DIFFERENT"}]),
        ("POST", "/items"): (400, {"error": "a different message"}),
    }
    with serve(variant) as url:
        result = replay(url, golden)
    assert result.passed == 2  # volatile ignored; message text tolerated
    assert result.strict_passed == 1  # exact message text differs


def test_wrong_status_values_and_missing_fields_fail() -> None:
    with serve(ROUTES) as url:
        golden = capture(url, SCRIPT, {}, "unit")
    wrong = {
        ("GET", "/items"): (200, [{"id": 2}]),  # wrong value + missing "name"
        ("POST", "/items"): (200, {"error": "name is required"}),  # wrong status
    }
    with serve(wrong) as url:
        result = replay(url, golden)
    assert result.passed == 0
    notes = result.to_dict()["failures"]
    assert any("status expected 400" in n for f in notes for n in f["notes"])
    assert result.field_match_rate is not None and result.field_match_rate < 1.0


def test_unsupported_golden_version() -> None:
    with pytest.raises(GoldenError):
        replay("http://127.0.0.1:1", {"schema_version": "9.9", "interactions": []})


FEATURE = """\
@FEAT-001 @generated
Feature: Items

  @BEAN-001 @FEAT-001 @generated
  Scenario: POST /items succeeds
    Given the service is running and the client is authenticated
    When the client sends POST /items with "name"
    Then the response status is 201
    And the body contains "id", "name"

  @BEAN-001 @FEAT-001 @generated
  Scenario: POST /items rejects a missing name
    Given the service is running
    When the client sends POST /items without "name"
    Then the request is rejected with a client error

  @BEAN-002 @FEAT-001 @generated
  Scenario: Invariant: Item.name is required
    Given the service is running
    When a change would violate "Item.name: required"
    Then the change is rejected

  @BEAN-003 @FEAT-001 @generated
  Scenario Outline: state change
    Given a thing in state "<state>"
    When the transition is requested
    Then the transition is rejected

    Examples:
      | state |
      | A |
"""


def test_gherkin_parse_and_bind() -> None:
    scenarios = parse_feature(FEATURE, "f.feature")
    assert [s.name for s in scenarios][:2] == [
        "POST /items succeeds",
        "POST /items rejects a missing name",
    ]
    assert (
        scenarios[0].tags == ["@BEAN-001", "@FEAT-001", "@generated"]
        and scenarios[3].outline
    )
    contract = {
        "paths": {
            "/items": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"properties": {"name": {"type": "string"}}}
                            }
                        }
                    }
                }
            }
        }
    }
    routes: dict[tuple[str, str], tuple[int, Any]] = {
        ("POST", "/items"): (201, {"id": 1, "name": "x"})
    }
    with serve(routes) as url:
        run = run_scenarios(url, scenarios, contract, {"X-API-Key": "k"})
    by = {r.name: r.status for r in run.results}
    assert by["POST /items succeeds"] == "passed"
    assert (
        by["POST /items rejects a missing name"] == "failed"
    )  # server returned 201, not 4xx
    assert (
        by["Invariant: Item.name is required"] == "unbound"
        and by["state change"] == "unbound"
    )
    assert run.bound == 2 and run.pass_rate == 0.5


def test_gherkin_files_generated_by_harvester_parse(tmp_path: Path) -> None:
    (tmp_path / "a.feature").write_text(FEATURE)
    assert len(load_scenarios(tmp_path)) == 4


def test_schema_diff(tmp_path: Path) -> None:
    orig = tmp_path / "o" / "db-design"
    reb = tmp_path / "r" / "db-design"
    orig.mkdir(parents=True)
    reb.mkdir(parents=True)
    (orig / "schema.sql").write_text(
        'CREATE TABLE "a" ("id" INTEGER PRIMARY KEY, "n" TEXT);\n'
        'CREATE TABLE "b" ("id" INTEGER PRIMARY KEY, "a_id" INTEGER, FOREIGN KEY ("a_id") REFERENCES "a" ("id"));\n'
    )
    (reb / "schema.sql").write_text(
        "CREATE TABLE a (id INTEGER PRIMARY KEY, n TEXT);\nCREATE TABLE b (id INTEGER PRIMARY KEY);\n"
    )
    diff = diff_schemas(tmp_path / "o", tmp_path / "r")
    assert diff is not None
    assert (diff.tables_found, diff.columns_found, diff.fks_found) == (2, 3, 0)
    assert diff.missing_columns == ["b.a_id"] and 0 < diff.score < 1
    assert diff_schemas(tmp_path / "r", tmp_path / "o") is not None
    assert diff_schemas(tmp_path / "none", tmp_path / "o") is None


def test_report_weights_and_na_are_not_free_passes() -> None:
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    empty = ParityReport()
    assert empty.overall is None and not empty.passed
    with serve(ROUTES) as url:
        golden = capture(url, SCRIPT, {}, "unit")
        report = ParityReport(golden=replay(url, golden))
    assert report.overall == 1.0 and report.passed
    assert "N/A" in report.to_markdown()


def test_app_under_test_never_inherits_host_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rebuilt app is untrusted: host API keys must not reach it."""
    import sys

    from repo_mirror_kit.harvester.parity.server import AppProcess

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-leak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "also-secret")
    (tmp_path / "start.sh").write_text(
        f'#!/usr/bin/env bash\nenv > "{tmp_path}/env.txt"\nexec {sys.executable} -m http.server "$PORT" --bind 127.0.0.1\n'
    )
    with AppProcess(tmp_path, "bash start.sh", {"API_KEY": "demo-key"}):
        pass
    seen = (tmp_path / "env.txt").read_text()
    names = {line.split("=", 1)[0] for line in seen.splitlines() if "=" in line}
    # Compare names/booleans only: a failure message must never echo env values.
    assert "API_KEY=demo-key" in seen and "PORT" in names
    assert "ANTHROPIC_API_KEY" not in names and "AWS_SECRET_ACCESS_KEY" not in names
    assert not any(
        n.endswith(("_API_KEY", "_TOKEN", "_SECRET")) for n in names - {"API_KEY"}
    )
