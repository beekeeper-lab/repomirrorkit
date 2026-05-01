"""Tests for the RUNBOOK.md generator (BEAN-053)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    BuildDeploySurface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.generator.runbook_md import generate_runbook_md


def _bd(
    name: str,
    config_type: str,
    tool: str = "",
    stages: list[str] | None = None,
    targets: list[str] | None = None,
) -> BuildDeploySurface:
    return BuildDeploySurface(
        name=name,
        config_type=config_type,
        tool=tool,
        stages=stages or [],
        targets=targets or [],
    )


class TestGenerateRunbookMd:
    def test_writes_file_to_top_level(self, tmp_path: Path) -> None:
        path = generate_runbook_md(SurfaceCollection(), tmp_path)
        assert path == tmp_path / "RUNBOOK.md"
        assert path.is_file()

    def test_empty_surfaces_renders_all_sections_empty(self, tmp_path: Path) -> None:
        text = generate_runbook_md(SurfaceCollection(), tmp_path).read_text()
        # Each group heading present even when empty.
        for heading in (
            "### Build Tools (0)",
            "### CI / CD (0)",
            "### Containers (0)",
            "### Infrastructure as Code (0)",
            "### Platform / Deploy Targets (0)",
        ):
            assert heading in text
        # Operations matrix is present.
        assert "## Operations Quick Reference" in text
        # All operations show their "(none detected)" hint when nothing matches.
        for op in (
            "Install",
            "Dev / Run",
            "Test",
            "Lint / Format",
            "Build",
            "Deploy / Release",
        ):
            assert op in text

    def test_groups_by_config_type(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            build_deploy=[
                _bd("Dockerfile", "container", "docker", stages=["build", "runtime"]),
                _bd(
                    "Makefile",
                    "build_tool",
                    "make",
                    targets=["install", "test", "build"],
                ),
                _bd(
                    ".github/workflows/ci.yml",
                    "ci_cd",
                    "github-actions",
                    stages=["lint", "test"],
                ),
            ],
        )
        text = generate_runbook_md(coll, tmp_path).read_text()
        assert "### Build Tools (1)" in text
        assert "### CI / CD (1)" in text
        assert "### Containers (1)" in text
        # Each tool's path and stages render.
        assert "Dockerfile" in text
        assert "Makefile" in text
        assert "github-actions" in text
        assert "`install`" in text
        assert "`test`" in text

    def test_operations_matrix_matches_install(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            build_deploy=[
                _bd(
                    "Makefile",
                    "build_tool",
                    "make",
                    targets=["install", "deps", "test", "build"],
                ),
            ],
        )
        text = generate_runbook_md(coll, tmp_path).read_text()
        # The Operations table should list both install + deps under Install,
        # both citing Makefile.
        # Find the Install row.
        assert "| Install | `install` | `Makefile` |" in text
        assert "| Install | `deps` | `Makefile` |" in text

    def test_operations_matrix_matches_test_lint_build_deploy(
        self, tmp_path: Path
    ) -> None:
        coll = SurfaceCollection(
            build_deploy=[
                _bd(
                    "Makefile",
                    "build_tool",
                    "make",
                    targets=["test", "lint", "build", "deploy"],
                ),
            ],
        )
        text = generate_runbook_md(coll, tmp_path).read_text()
        assert "| Test | `test` | `Makefile` |" in text
        assert "| Lint / Format | `lint` | `Makefile` |" in text
        assert "| Build | `build` | `Makefile` |" in text
        assert "| Deploy / Release | `deploy` | `Makefile` |" in text

    def test_operations_unmatched_show_gap_hint(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            build_deploy=[
                _bd("Makefile", "build_tool", "make", targets=["test"]),
            ],
        )
        text = generate_runbook_md(coll, tmp_path).read_text()
        # Install/Build/Deploy missing — gap hint should appear for each.
        # Use a fragment of the gap hint.
        assert (
            text.count("(none detected — recreated project should still provide one)")
            >= 3
        )

    def test_total_count_in_header(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            build_deploy=[
                _bd("Dockerfile", "container", "docker"),
                _bd("Makefile", "build_tool", "make"),
            ]
        )
        text = generate_runbook_md(coll, tmp_path).read_text()
        assert "Total build/deploy surfaces detected:** 2" in text

    def test_dedupes_identical_stage_source_pairs_in_matrix(
        self, tmp_path: Path
    ) -> None:
        coll = SurfaceCollection(
            build_deploy=[
                _bd(
                    "Makefile", "build_tool", "make", stages=["test"], targets=["test"]
                ),
            ]
        )
        text = generate_runbook_md(coll, tmp_path).read_text()
        # Matrix row for (test, Makefile) should appear exactly once even
        # though the label appears in both stages and targets.
        assert text.count("| Test | `test` | `Makefile` |") == 1
