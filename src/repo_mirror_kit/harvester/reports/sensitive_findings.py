"""Sensitive-findings report writer (BEAN-083).

Renders ``reports/sensitive-findings.{md,json}`` from the findings collected
by the redaction post-pass. The report carries metadata only — category,
kind, ``file:line``, surface, placeholder, and a hash prefix — never any raw
value material.
"""

from __future__ import annotations

import json
from pathlib import Path

from repo_mirror_kit.harvester.redaction import (
    SensitiveFinding,
    _iter_findings_sorted,
)

_INTRO = (
    "Sensitive-shaped values were detected in the source and **redacted** "
    "before any bean, report, or generated artifact was written. This report "
    "lists *where* each was found so the repository owner can act (rotate "
    "credentials, scrub history). The raw values are intentionally **not** "
    "recorded anywhere — only the metadata below.\n"
)


def render_sensitive_findings_md(findings: list[SensitiveFinding]) -> str:
    """Render the human-readable ``sensitive-findings.md`` content."""
    lines = ["# Sensitive Findings", ""]
    lines.append(f"**{len(findings)}** sensitive value(s) found and redacted.")
    lines.append("")
    lines.append(_INTRO)
    lines.append(
        "> Secrets committed to source are a bad practice. Rotate any real "
        "credentials and remove them from history."
    )
    lines.append("")
    lines.append("| Category | Kind | Location | Surface | Placeholder | Hash prefix |")
    lines.append("|----------|------|----------|---------|-------------|-------------|")
    for f in _iter_findings_sorted(findings):
        location = f.file or "(unknown)"
        if f.line is not None:
            location = f"{location}:{f.line}"
        surface = f"{f.surface_name} ({f.surface_type})"
        lines.append(
            f"| {f.category} | {f.kind} | {location} | {surface} "
            f"| `{f.placeholder}` | `{f.hash_prefix}` |"
        )
    lines.append("")
    return "\n".join(lines)


def write_sensitive_findings_report(
    output_dir: Path,
    findings: list[SensitiveFinding],
) -> tuple[Path, Path]:
    """Write ``sensitive-findings.{md,json}`` under ``reports/``.

    Args:
        output_dir: The harvest output root.
        findings: The (deduplicated) findings to report.

    Returns:
        A tuple of the written ``(md_path, json_path)``.
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    md_path = reports_dir / "sensitive-findings.md"
    json_path = reports_dir / "sensitive-findings.json"

    md_path.write_text(render_sensitive_findings_md(findings), encoding="utf-8")

    payload = {
        "count": len(findings),
        "findings": [f.to_dict() for f in _iter_findings_sorted(findings)],
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return md_path, json_path
