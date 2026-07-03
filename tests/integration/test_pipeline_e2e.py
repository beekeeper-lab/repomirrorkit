"""End-to-end harvester pipeline tests against fixture projects (BEAN-050).

Marked with ``@pytest.mark.integration``. Run with::

    uv run pytest tests/integration/

To skip during unit-only runs::

    uv run pytest -m "not integration"
"""

from __future__ import annotations

import json
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

    # BEAN-051: top-level REQUIREMENTS.md exists with the expected sections.
    requirements = out / "REQUIREMENTS.md"
    assert requirements.is_file(), "Top-level REQUIREMENTS.md missing"
    text = requirements.read_text()
    assert "Requirements Specification" in text
    assert "## Tech Stack" in text
    assert "## Functional Requirements" in text

    # BEAN-062: the POST /api/users endpoint gets populated request AND
    # response contracts (rendered as field tables in its API bean).
    api_beans = [
        p.read_text()
        for p in bean_files
        if "post-api-users" in p.name.lower() or "POST /api/users" in p.read_text()
    ]
    assert api_beans, "Expected an API bean for POST /api/users"
    post_bean = api_beans[0]
    assert "| `name` |" in post_bean, "Request field table missing 'name'"
    assert "| `email` |" in post_bean, "Request field table missing 'email'"
    assert "_Confidence: inferred._" in post_bean
    assert "| `id` |" in post_bean, "Response field table missing 'id'"

    # BEAN-071: OpenAPI 3.1 contract generated with populated operations.
    contract_file = out / "api-contract.json"
    assert contract_file.is_file(), "api-contract.json missing"
    contract = json.loads(contract_file.read_text())
    assert contract["openapi"] == "3.1.0"
    post_op = contract["paths"]["/api/users"]["post"]
    body = post_op["requestBody"]["content"]["application/json"]["schema"]
    assert "name" in body["properties"]
    assert "email" in body["properties"]
    assert "name" in body.get("required", [])

    # BEAN-076: fidelity metrics in coverage.json; the Flask fixture's
    # contracts are fully determined, so the API metrics pin at 100%.
    coverage = json.loads((out / "reports" / "coverage.json").read_text())
    fidelity = coverage["fidelity"]
    metrics = {m["name"]: m for m in fidelity["metrics"]}
    assert metrics["api_request_contracts"]["percentage"] == 100.0
    assert metrics["api_response_contracts"]["percentage"] == 100.0
    assert metrics["screen_field_mappings"]["applicable"] is False
    assert result.fidelity_passed is True
    coverage_md = (out / "reports" / "coverage.md").read_text()
    assert "## Fidelity (recreation-readiness)" in coverage_md


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

    # BEAN-051: top-level REQUIREMENTS.md exists.
    assert (out / "REQUIREMENTS.md").is_file(), "REQUIREMENTS.md missing"
