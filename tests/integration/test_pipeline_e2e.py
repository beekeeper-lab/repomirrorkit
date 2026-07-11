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
from repo_mirror_kit.harvester.pipeline import HarvestPipeline, HarvestResult


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

    # BEAN-066: seed/reference datasets — the fixture's UserStatus enum and
    # the roles lookup table both yield seed-data beans with actual values.
    all_beans_text = "\n".join(p.read_text() for p in (out / "beans").glob("BEAN-*.md"))
    assert "UserStatus" in all_beans_text, "UserStatus enum bean missing"
    assert "suspended" in all_beans_text, "Enum values missing from beans"
    assert "admin" in all_beans_text, "roles lookup values missing from beans"


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


# ---------------------------------------------------------------------------
# BEAN-080: Stage H cleanup + provenance + resume-after-cleanup
# ---------------------------------------------------------------------------


def _run_cleanup_pipeline(fixture_path: Path, output_dir: Path) -> HarvestResult:
    """Run the pipeline with Stage H cleanup enabled (no LLM)."""
    config = HarvestConfig(
        repo=str(fixture_path),
        out=output_dir,
        log_level="warn",
        llm_enabled=False,
        fail_on_gaps=False,
        cleanup=True,
    )
    return HarvestPipeline().run(config)


@pytest.mark.integration
def test_cleanup_removes_source_and_all_git(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """After a --cleanup run: repo/ gone, zero .git anywhere, beans intact."""
    repo = local_git_repo("python-flask")
    out = tmp_path / "harvest-out"

    result = _run_cleanup_pipeline(repo, out)

    assert result.success, (
        f"Pipeline failed at stage {result.error_stage}: {result.error_message}"
    )
    assert result.cleanup_performed is True
    assert not (out / "repo").exists(), "repo/ must be removed by Stage H"
    assert list(out.rglob(".git")) == [], "no .git may remain anywhere"
    # The requirements package itself is intact.
    assert (out / "beans").is_dir()
    assert len(list((out / "beans").glob("BEAN-*.md"))) >= 2
    assert (out / "REQUIREMENTS.md").is_file()


@pytest.mark.integration
def test_cleanup_records_provenance(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """Provenance (URL + HEAD SHA) survives in state.json and REQUIREMENTS.md."""
    repo = local_git_repo("python-flask")
    out = tmp_path / "harvest-out"

    result = _run_cleanup_pipeline(repo, out)
    assert result.success

    state = json.loads((out / "state" / "state.json").read_text())
    prov = state["provenance"]
    assert prov["repo_url"] == str(repo)
    assert isinstance(prov["head_sha"], str) and len(prov["head_sha"]) == 40
    assert state["cleanup"]["removed"] is True
    assert state["cleanup"]["files_removed"] > 0

    requirements = (out / "REQUIREMENTS.md").read_text()
    assert prov["head_sha"] in requirements
    assert "not** included" in requirements  # source-removed provenance note


@pytest.mark.integration
def test_keep_source_preserves_repo(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    repo = local_git_repo("python-flask")
    out = tmp_path / "harvest-out"

    config = HarvestConfig(
        repo=str(repo),
        out=out,
        log_level="warn",
        llm_enabled=False,
        fail_on_gaps=False,
        cleanup=True,
        keep_source=True,
    )
    result = HarvestPipeline().run(config)

    assert result.success
    assert result.cleanup_performed is False
    assert (out / "repo").is_dir(), "--keep-source must preserve the clone"


@pytest.mark.integration
def test_resume_after_cleanup_reclones(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """--resume on a cleaned output dir re-clones instead of failing (BEAN-080)."""
    repo = local_git_repo("python-flask")
    out = tmp_path / "harvest-out"

    first = _run_cleanup_pipeline(repo, out)
    assert first.success and first.cleanup_performed
    assert not (out / "repo").exists()

    config = HarvestConfig(
        repo=str(repo),
        out=out,
        log_level="warn",
        llm_enabled=False,
        fail_on_gaps=False,
        cleanup=True,
        resume=True,
    )
    second = HarvestPipeline().run(config)

    assert second.success, (
        f"Resume failed at stage {second.error_stage}: {second.error_message}"
    )
    assert second.bean_count > 0
    assert second.cleanup_performed is True
    assert not (out / "repo").exists()


@pytest.mark.integration
def test_mirror_pipeline_end_to_end(
    local_git_repo: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full mirror-mode run with enrichment stubbed out (no network)."""
    import repo_mirror_kit.harvester.llm as llm_pkg

    # Stage C2 imports enrich_surfaces from the llm package at call time.
    monkeypatch.setattr(llm_pkg, "enrich_surfaces", lambda surfaces, *a, **k: surfaces)

    repo = local_git_repo("python-flask")
    out = tmp_path / "harvest-out"
    config = HarvestConfig(
        repo=str(repo),
        out=out,
        log_level="warn",
        llm_api_key="sk-ant-test",  # mirror requires a key; client never called
        fail_on_gaps=False,
        fail_on_fidelity=False,  # fixture depth gates are BEAN-081/082 turf
        mirror=True,
    )
    result = HarvestPipeline().run(config)

    assert result.success, (
        f"Mirror run failed at stage {result.error_stage}: {result.error_message}"
    )
    assert result.cleanup_performed is True
    assert not (out / "repo").exists()
    assert list(out.rglob(".git")) == []
    assert (out / "REQUIREMENTS.md").is_file()
