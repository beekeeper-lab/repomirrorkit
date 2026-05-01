"""Tests for the top-level REQUIREMENTS.md aggregator (BEAN-051)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ConfigSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.generator.requirements_md import (
    generate_requirements_md,
)


def _bean(
    n: int,
    surface_type: str,
    title: str,
    output_dir: Path,
) -> WrittenBean:
    bean_id = f"BEAN-{n:03d}"
    slug = title.lower().replace(" ", "-")
    return WrittenBean(
        bean_number=n,
        bean_id=bean_id,
        slug=slug,
        surface_type=surface_type,
        title=title,
        path=output_dir / "beans" / f"{bean_id}-{slug}.md",
        skipped=False,
    )


def _make_surfaces() -> SurfaceCollection:
    return SurfaceCollection(
        routes=[
            RouteSurface(
                name="ListUsers",
                path="/api/users",
                method="GET",
                source_refs=[SourceRef(file_path="app.py", start_line=13)],
            ),
        ],
        apis=[
            ApiSurface(
                name="GetUserById",
                method="GET",
                path="/api/users/{id}",
                source_refs=[SourceRef(file_path="app.py", start_line=20)],
            ),
        ],
        models=[
            ModelSurface(
                name="User",
                source_refs=[SourceRef(file_path="models.py", start_line=8)],
            ),
        ],
        config=[
            ConfigSurface(
                name="DATABASE_URL",
                source_refs=[SourceRef(file_path="app.py", start_line=5)],
            ),
        ],
    )


def _make_profile() -> StackProfile:
    return StackProfile(
        stacks={"python": 0.95, "flask": 0.90},
        evidence={
            "python": ["pyproject.toml", "app.py"],
            "flask": ["requirements.txt"],
        },
        signals=[],
    )


class TestGenerateRequirementsMd:
    def test_writes_file_to_top_level(self, tmp_path: Path) -> None:
        path = generate_requirements_md(
            project_name="TestProject",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=[],
            output_dir=tmp_path,
        )
        assert path == tmp_path / "REQUIREMENTS.md"
        assert path.is_file()

    def test_includes_project_name_and_bean_count_in_header(
        self, tmp_path: Path
    ) -> None:
        beans = [
            _bean(1, "route", "ListUsers", tmp_path),
            _bean(2, "model", "User", tmp_path),
        ]
        path = generate_requirements_md(
            project_name="MyProject",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=beans,
            output_dir=tmp_path,
        )
        text = path.read_text()
        assert "MyProject" in text
        assert "Total beans | 2" in text

    def test_tech_stack_table_lists_detected_stacks(self, tmp_path: Path) -> None:
        path = generate_requirements_md(
            project_name="X",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=[],
            output_dir=tmp_path,
        )
        text = path.read_text()
        assert "## Tech Stack" in text
        assert "python" in text
        assert "flask" in text
        # Confidence and evidence sample
        assert "0.95" in text
        assert "pyproject.toml" in text

    def test_all_section_headings_present_even_when_empty(
        self, tmp_path: Path
    ) -> None:
        # Empty surfaces — every section should still be there with a
        # "(none detected)"-style hint.
        path = generate_requirements_md(
            project_name="Empty",
            surfaces=SurfaceCollection(),
            profile=StackProfile(),
            beans=[],
            output_dir=tmp_path,
        )
        text = path.read_text()
        for heading in (
            "### Routes / Pages (0)",
            "### APIs (0)",
            "### Data Models (0)",
            "### Authentication & Authorization (0)",
            "### Configuration & Environment (0)",
            "### Testing (0)",
            "### Build & Deploy (0)",
        ):
            assert heading in text

    def test_surface_rows_link_to_bean_files(self, tmp_path: Path) -> None:
        beans = [
            _bean(1, "route", "ListUsers", tmp_path),
            _bean(2, "model", "User", tmp_path),
        ]
        path = generate_requirements_md(
            project_name="X",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=beans,
            output_dir=tmp_path,
        )
        text = path.read_text()
        # Bean ID appears as link text.
        assert "[BEAN-001](beans/BEAN-001-listusers.md)" in text
        assert "[BEAN-002](beans/BEAN-002-user.md)" in text

    def test_pipe_in_surface_name_is_escaped(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="Bad|Name",
                    path="/x",
                    method="GET",
                    source_refs=[SourceRef(file_path="x.py")],
                ),
            ]
        )
        path = generate_requirements_md(
            project_name="X",
            surfaces=coll,
            profile=StackProfile(),
            beans=[],
            output_dir=tmp_path,
        )
        text = path.read_text()
        # Escaped form, not the raw pipe (which would corrupt the table).
        assert "Bad\\|Name" in text

    def test_reports_footer_links_present(self, tmp_path: Path) -> None:
        path = generate_requirements_md(
            project_name="X",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=[],
            output_dir=tmp_path,
        )
        text = path.read_text()
        assert "[Coverage report](reports/coverage.md)" in text
        assert "[Gap analysis](reports/gaps.md)" in text
        assert "[Surface map](reports/surface-map.md)" in text
        assert "[`beans/`](beans/)" in text
        assert "[`project-folder/`](project-folder/)" in text

    def test_source_refs_show_file_and_line(self, tmp_path: Path) -> None:
        path = generate_requirements_md(
            project_name="X",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=[],
            output_dir=tmp_path,
        )
        text = path.read_text()
        # Routes surface has app.py:13
        assert "`app.py:13`" in text

    def test_section_heading_count_reflects_surface_count(
        self, tmp_path: Path
    ) -> None:
        path = generate_requirements_md(
            project_name="X",
            surfaces=_make_surfaces(),
            profile=_make_profile(),
            beans=[],
            output_dir=tmp_path,
        )
        text = path.read_text()
        # 1 route, 1 api, 1 model, 1 config in _make_surfaces()
        assert "### Routes / Pages (1)" in text
        assert "### APIs (1)" in text
        assert "### Data Models (1)" in text
        assert "### Configuration & Environment (1)" in text
