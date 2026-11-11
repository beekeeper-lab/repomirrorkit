"""Combine parity families into one report (BEAN-078).

Three families, each reported separately so a regression is attributable:

``golden_replay``  recorded request→response interactions replayed against the
                   rebuild (status + field-level body match; message text
                   tolerated in the headline score, exact in ``strict``)
``gherkin``        generated scenarios bound to HTTP; scored *relative to the
                   scenarios the original app passes* when the original is also
                   run (calibration), else raw pass-rate over bound scenarios
``schema``         tables / columns / foreign keys of the database design

Overall = weighted mean over the **applicable** families (weights below,
re-normalised); a family with nothing to measure is N/A, never a free 100%.
The schema family applies only when the rebuild itself has a relational
database design — a rebuild may legitimately store data some other way.
The north-star gate is ``DEFAULT_THRESHOLD`` (0.90).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_mirror_kit.harvester.parity.gherkin_runner import (
    GherkinRun,
    load_contract,
    load_scenarios,
    run_scenarios,
)
from repo_mirror_kit.harvester.parity.goldens import ReplayResult, replay
from repo_mirror_kit.harvester.parity.schema_diff import SchemaDiff, diff_schemas
from repo_mirror_kit.harvester.parity.server import AppProcess

DEFAULT_THRESHOLD = 0.90
WEIGHTS = {"golden_replay": 0.5, "gherkin": 0.3, "schema": 0.2}
REPORT_VERSION = "1.0"


@dataclass
class ParityReport:
    golden: ReplayResult | None = None
    gherkin: dict[str, Any] | None = None
    gherkin_relative: float | None = None
    gherkin_original_pass_rate: float | None = None
    schema: SchemaDiff | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)
    threshold: float = DEFAULT_THRESHOLD
    notes: list[str] = field(default_factory=list)

    def family_scores(self) -> dict[str, float | None]:
        gherkin_score = self.gherkin_relative
        if gherkin_score is None and self.gherkin is not None:
            gherkin_score = self.gherkin.get("pass_rate")
        return {
            "golden_replay": self.golden.pass_rate if self.golden else None,
            "gherkin": gherkin_score,
            "schema": self.schema.score if self.schema else None,
        }

    @property
    def overall(self) -> float | None:
        scores = {k: v for k, v in self.family_scores().items() if v is not None}
        if not scores:
            return None
        weight = sum(WEIGHTS[k] for k in scores)
        return sum(WEIGHTS[k] * v for k, v in scores.items()) / weight

    @property
    def passed(self) -> bool:
        return self.overall is not None and self.overall >= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": REPORT_VERSION,
            "overall": self.overall,
            "threshold": self.threshold,
            "passed": self.passed,
            "weights": WEIGHTS,
            "families": {
                "golden_replay": {
                    "score": self.golden.pass_rate if self.golden else None,
                    **(self.golden.to_dict() if self.golden else {}),
                },
                "gherkin": {
                    "score": self.family_scores()["gherkin"],
                    "original_pass_rate": self.gherkin_original_pass_rate,
                    "relative_to_original": self.gherkin_relative,
                    **(self.gherkin or {}),
                },
                "schema": {
                    "score": self.schema.score if self.schema else None,
                    **(self.schema.to_dict() if self.schema else {}),
                },
            },
            "telemetry": self.telemetry,
            "notes": self.notes,
        }

    def to_markdown(self) -> str:
        def pct(v: float | None) -> str:
            return "N/A" if v is None else f"{100 * v:.1f}%"

        scores = self.family_scores()
        lines = [
            "# Parity report",
            "",
            f"**Overall:** {pct(self.overall)} — gate {pct(self.threshold)}: "
            f"**{'PASS' if self.passed else 'FAIL'}**",
            "",
            "| Family | Score | Detail |",
            "|--------|-------|--------|",
        ]
        if self.golden:
            g = self.golden
            lines.append(
                f"| Golden replay | {pct(scores['golden_replay'])} | "
                f"{g.passed}/{g.total} interactions (strict {g.strict_passed}/{g.total}); "
                f"field match {pct(g.field_match_rate)} |"
            )
        else:
            lines.append("| Golden replay | N/A | no goldens supplied |")
        if self.gherkin:
            gh = self.gherkin
            rel = (
                f"; relative to original {pct(self.gherkin_relative)} "
                f"(original passes {pct(self.gherkin_original_pass_rate)})"
                if self.gherkin_relative is not None
                else ""
            )
            lines.append(
                f"| Gherkin | {pct(scores['gherkin'])} | {gh['passed']}/{gh['bound']} bound "
                f"({gh['unbound']} unbound){rel} |"
            )
        else:
            lines.append("| Gherkin | N/A | no scenarios |")
        if self.schema:
            s = self.schema
            lines.append(
                f"| Schema | {pct(s.score)} | tables {s.tables_found}/{s.tables_expected}, "
                f"columns {s.columns_found}/{s.columns_expected}, FKs {s.fks_found}/{s.fks_expected} |"
            )
        else:
            lines.append("| Schema | N/A | original has no database design |")
        if self.telemetry:
            lines += [
                "",
                "## Run telemetry",
                "",
                "```json",
                json.dumps(self.telemetry, indent=2),
                "```",
            ]
        failures = self.golden.to_dict()["failures"] if self.golden else []
        if failures:
            lines += ["", "## Golden replay failures", ""]
            for f in failures[:15]:
                lines.append(
                    f"- **{f['name']}** — expected {f['status_expected']}, got {f['status_actual']}; {'; '.join(f['notes'][:2])}"
                )
        if self.notes:
            lines += ["", "## Notes", ""] + [f"- {n}" for n in self.notes]
        return "\n".join(lines) + "\n"


def score_rebuild(
    *,
    golden: dict[str, Any] | None,
    original_harvest: Path,
    rebuild_dir: Path,
    rebuild_harvest: Path | None,
    auth_headers: dict[str, str],
    env: dict[str, str] | None = None,
    start_command: str = "bash start.sh",
    original_dir: Path | None = None,
    original_start_command: str = "bash start.sh",
    telemetry: dict[str, Any] | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    startup_timeout: float = 180.0,
) -> ParityReport:
    """Run the rebuild (and optionally the original) and score parity."""
    report = ParityReport(telemetry=telemetry or {}, threshold=threshold)
    scenarios = load_scenarios(original_harvest / "gherkin")
    contract = load_contract(original_harvest)

    original_run: GherkinRun | None = None
    if original_dir is not None and scenarios:
        with AppProcess(
            original_dir, original_start_command, env, startup_timeout
        ) as app:
            original_run = run_scenarios(
                app.base_url, scenarios, contract, auth_headers
            )
        report.gherkin_original_pass_rate = original_run.pass_rate
        report.notes.append(
            f"Gherkin suite calibrated against the original: it passes "
            f"{len(original_run.passed_names)}/{original_run.bound} bound scenarios."
        )

    with AppProcess(rebuild_dir, start_command, env, startup_timeout) as app:
        if golden is not None:
            report.golden = replay(app.base_url, golden)
        if scenarios:
            run = run_scenarios(app.base_url, scenarios, contract, auth_headers)
            report.gherkin = run.to_dict()
            if original_run is not None and original_run.passed_names:
                reference = original_run.passed_names
                report.gherkin_relative = len(run.passed_names & reference) / len(
                    reference
                )

    if rebuild_harvest is not None:
        if (rebuild_harvest / "db-design" / "schema.sql").is_file():
            report.schema = diff_schemas(original_harvest, rebuild_harvest)
        elif (original_harvest / "db-design" / "schema.sql").is_file():
            # Storage is an implementation choice: a rebuild that keeps its
            # data elsewhere (in memory, a document store, ...) is not scored
            # on tables it never claimed to have. Its data *shape* is still
            # verified through the golden replay and Gherkin families.
            report.notes.append(
                "Schema family N/A: the rebuild exposes no relational database "
                "design (storage is an implementation choice); entity fields are "
                "covered by golden replay."
            )
    return report


def write_report(out_dir: Path, report: ParityReport) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath = out_dir / "parity-report.json"
    mpath = out_dir / "parity-report.md"
    jpath.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    mpath.write_text(report.to_markdown(), encoding="utf-8")
    return jpath, mpath
