"""End-to-end harvester pipeline tests against fixture projects (BEAN-050).

Marked with ``@pytest.mark.integration``. Run with::

    uv run pytest tests/integration/

To skip during unit-only runs::

    uv run pytest -m "not integration"
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.pipeline import HarvestPipeline


def _run_pipeline(fixture_path: Path, output_dir: Path) -> object:
    """Run the full harvester pipeline against a local fixture path."""
    config = HarvestConfig(
        repo=str(fixture_path),
        out=output_dir,
        log_level="warn",
        llm_enabled=False,
        fail_on_gaps=False,
    )
    return HarvestPipeline().run(config)


@pytest.mark.integration
def test_pipeline_python_flask_fixture(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """Full pipeline runs cleanly on the Flask fixture and produces beans + project folder."""
    repo = local_git_repo("python-flask")
    out = tmp_path / "harvest-out"

    result = _run_pipeline(repo, out)

    assert result.success, (
        f"Pipeline failed at stage {result.error_stage}: {result.error_message}"
    )
    assert result.bean_count > 0, "Expected at least one bean to be generated"
    assert (out / "project-folder").is_dir(), "Stage G project-folder missing"
    assert (out / "beans").is_dir(), "Stage E beans dir missing"

    bean_files = list((out / "beans").glob("BEAN-*.md"))
    assert len(bean_files) >= 2, (
        f"Expected >=2 beans for the Flask fixture, got {len(bean_files)}"
    )


@pytest.mark.integration
def test_pipeline_ts_next_fixture(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """Full pipeline runs cleanly on the Next.js fixture and produces beans + project folder."""
    repo = local_git_repo("ts-next")
    out = tmp_path / "harvest-out"

    result = _run_pipeline(repo, out)

    assert result.success, (
        f"Pipeline failed at stage {result.error_stage}: {result.error_message}"
    )
    assert result.bean_count > 0, "Expected at least one bean to be generated"
    assert (out / "project-folder").is_dir(), "Stage G project-folder missing"

    bean_files = list((out / "beans").glob("BEAN-*.md"))
    assert len(bean_files) >= 2, (
        f"Expected >=2 beans for the Next.js fixture, got {len(bean_files)}"
    )
