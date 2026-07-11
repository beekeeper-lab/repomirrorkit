"""Tests for the sensitive-findings report writer (BEAN-083)."""

from __future__ import annotations

import json
from pathlib import Path

from repo_mirror_kit.harvester.redaction import SensitiveFinding
from repo_mirror_kit.harvester.reports.sensitive_findings import (
    write_sensitive_findings_report,
)


def _finding() -> SensitiveFinding:
    return SensitiveFinding(
        category="secret",
        kind="aws-access-key",
        file="app/api.py",
        line=42,
        surface_name="create_user",
        surface_type="api",
        placeholder="[REDACTED:aws-access-key]",
        hash_prefix="abc123def456",
    )


def test_report_writes_md_and_json(tmp_path: Path) -> None:
    md_path, json_path = write_sensitive_findings_report(tmp_path, [_finding()])

    assert md_path == tmp_path / "reports" / "sensitive-findings.md"
    assert json_path == tmp_path / "reports" / "sensitive-findings.json"
    assert md_path.is_file()
    assert json_path.is_file()

    md = md_path.read_text(encoding="utf-8")
    assert "aws-access-key" in md
    assert "app/api.py:42" in md
    assert "[REDACTED:aws-access-key]" in md
    assert "abc123def456" in md

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["findings"][0]["kind"] == "aws-access-key"
    assert payload["findings"][0]["file"] == "app/api.py"
    # No raw-value key ever appears in the JSON schema.
    assert "value" not in payload["findings"][0]


def test_report_json_has_no_raw_value_material(tmp_path: Path) -> None:
    _, json_path = write_sensitive_findings_report(tmp_path, [_finding()])
    keys = set(json.loads(json_path.read_text())["findings"][0].keys())
    assert keys == {
        "category",
        "kind",
        "file",
        "line",
        "surface_name",
        "surface_type",
        "placeholder",
        "hash_prefix",
    }
