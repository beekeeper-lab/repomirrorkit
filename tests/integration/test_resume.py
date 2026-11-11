"""Resume / --from-stage behavior (BEAN-060)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from repo_mirror_kit.harvester import persistence
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.pipeline import HarvestPipeline


def _config(repo: Path, out: Path, **kw: object) -> HarvestConfig:
    return HarvestConfig(
        repo=str(repo),
        out=out,
        log_level="warn",
        llm_enabled=False,
        fail_on_gaps=False,
        **kw,  # type: ignore[arg-type]
    )


@pytest.mark.integration
@pytest.mark.parametrize("fixture", ["python-flask", "ts-next", "python-flask-factory"])
def test_surface_round_trip(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    out = tmp_path / "out"
    assert HarvestPipeline().run(_config(local_git_repo(fixture), out)).success
    data = json.loads((out / "state" / persistence.SURFACES_ARTIFACT).read_text())
    rebuilt = persistence.surface_collection_from_dict(data)
    assert rebuilt.to_dict() == data


@pytest.mark.integration
def test_resume_skips_analysis_and_regenerates_beans(
    local_git_repo: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = local_git_repo("python-flask")
    out = tmp_path / "out"
    first = HarvestPipeline().run(_config(repo, out))
    assert first.success
    before = sorted(p.name for p in (out / "beans").glob("BEAN-*.md"))

    import shutil

    shutil.rmtree(out / "beans")

    def boom(*a: object, **k: object) -> None:
        raise AssertionError("stage must not re-run on resume")

    for name in ("_run_stage_b", "_run_stage_c", "_run_stage_c2"):
        monkeypatch.setattr(HarvestPipeline, name, boom)

    second = HarvestPipeline().run(_config(repo, out, resume=True))
    assert second.success
    assert sorted(p.name for p in (out / "beans").glob("BEAN-*.md")) == before


@pytest.mark.integration
def test_from_stage_c2_reruns_only_enrichment_and_later(
    local_git_repo: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = local_git_repo("python-flask")
    out = tmp_path / "out"
    assert HarvestPipeline().run(_config(repo, out)).success

    calls: list[str] = []
    orig_c2 = HarvestPipeline._run_stage_c2

    def spy_c2(self: HarvestPipeline, *a: object, **k: object) -> object:
        calls.append("C2")
        return orig_c2(self, *a, **k)  # type: ignore[arg-type]

    def boom(*a: object, **k: object) -> None:
        raise AssertionError("B/C must not re-run")

    monkeypatch.setattr(HarvestPipeline, "_run_stage_c2", spy_c2)
    monkeypatch.setattr(HarvestPipeline, "_run_stage_b", boom)
    monkeypatch.setattr(HarvestPipeline, "_run_stage_c", boom)

    assert (
        HarvestPipeline().run(_config(repo, out, from_stage="C2", resume=True)).success
    )
    assert calls == ["C2"]


@pytest.mark.integration
def test_tampered_artifact_forces_rerun(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    repo = local_git_repo("python-flask")
    out = tmp_path / "out"
    assert HarvestPipeline().run(_config(repo, out)).success
    art = out / "state" / persistence.SURFACES_ARTIFACT
    art.write_text(art.read_text().replace("api", "xpi", 1))

    result = HarvestPipeline().run(_config(repo, out, resume=True))
    assert result.success
    # Re-extracted from source: artifact is valid again.
    json.loads(art.read_text())
    assert '"surface_type": "api"' in art.read_text()


@pytest.mark.integration
def test_config_change_invalidates_persisted_stages(
    local_git_repo: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = local_git_repo("python-flask")
    out = tmp_path / "out"
    assert HarvestPipeline().run(_config(repo, out)).success

    ran: list[str] = []
    orig = HarvestPipeline._run_stage_c

    def spy(self: HarvestPipeline, *a: object, **k: object) -> object:
        ran.append("C")
        return orig(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(HarvestPipeline, "_run_stage_c", spy)
    cfg = _config(repo, out, resume=True, exclude=("**/tests/**",))
    assert HarvestPipeline().run(cfg).success
    assert ran == ["C"]


@pytest.mark.integration
def test_resume_after_interrupt_at_stage_boundary(
    local_git_repo: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = local_git_repo("python-flask")
    out = tmp_path / "out"

    def interrupt(*a: object, **k: object) -> None:
        raise KeyboardInterrupt

    with monkeypatch.context() as m:
        m.setattr(HarvestPipeline, "_run_stage_c2", interrupt)
        with pytest.raises(KeyboardInterrupt):
            HarvestPipeline().run(_config(repo, out))

    def boom(*a: object, **k: object) -> None:
        raise AssertionError("B/C already completed before the interrupt")

    monkeypatch.setattr(HarvestPipeline, "_run_stage_b", boom)
    monkeypatch.setattr(HarvestPipeline, "_run_stage_c", boom)
    assert HarvestPipeline().run(_config(repo, out, resume=True)).success
