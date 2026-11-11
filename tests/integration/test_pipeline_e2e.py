"""End-to-end harvester pipeline tests against fixture projects (BEAN-050).

Marked with ``@pytest.mark.integration``. Run with::

    uv run pytest tests/integration/

To skip during unit-only runs::

    uv run pytest -m "not integration"
"""

from __future__ import annotations

import json
import subprocess
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
        if "type: api\n" in p.read_text() and "POST /api/users" in p.read_text()
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

    # BEAN-081: no bean carries a literal TODO placeholder (even on this
    # structural-only run); unknowns are declared as gaps instead, so
    # placeholder_free pins at 100%.
    for bean_path in (out / "beans").glob("BEAN-*.md"):
        assert "TODO:" not in bean_path.read_text(), f"TODO in {bean_path.name}"
    assert metrics["placeholder_free_beans"]["percentage"] == 100.0

    # BEAN-066: seed/reference datasets — the fixture's UserStatus enum and
    # the roles lookup table both yield seed-data beans with actual values.
    all_beans_text = "\n".join(p.read_text() for p in (out / "beans").glob("BEAN-*.md"))
    assert "UserStatus" in all_beans_text, "UserStatus enum bean missing"
    assert "suspended" in all_beans_text, "Enum values missing from beans"
    assert "admin" in all_beans_text, "roles lookup values missing from beans"

    # BEAN-082: exact-value extraction populates BEAN-081's rule tables with
    # real data (no LLM). The User model's constraints render a validation
    # table AND the GET /api/users/<id> endpoint's abort(404) renders an
    # error table — both exercised by the fixture.
    assert "| Field | Rule |" in all_beans_text, (
        "Model validation-rule table did not render exact rules"
    )
    assert "| Condition | Status |" in all_beans_text, (
        "API error-contract table did not render exact error states"
    )
    # The exact literals are copied verbatim, not paraphrased.
    assert "admin\\|member\\|guest" in all_beans_text, "enum members not verbatim"
    assert "User not found" in all_beans_text, "error message not verbatim"


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


@pytest.mark.integration
def test_sensitive_findings_redacted_end_to_end(tmp_path: Path) -> None:
    """BEAN-083: planted secrets/PII are redacted everywhere and reported.

    Builds a throwaway git repo (does NOT touch the shared fixtures) with a
    Python enum carrying a fake AWS key and an email, runs the harvester with
    ``--no-llm``, and asserts the raw values appear nowhere under the output
    dir while the findings are surfaced.
    """
    # 1. Build a throwaway source repo with planted secret + PII in an enum
    #    (captured structurally as seed data, no LLM required).
    src = tmp_path / "leaky-src"
    src.mkdir()
    (src / "models.py").write_text(
        "from enum import Enum\n"
        "\n"
        "\n"
        "class Secrets(Enum):\n"
        '    AWS = "AKIAIOSFODNN7EXAMPLE"\n'
        '    CONTACT = "alice@example.com"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    subprocess.run(["git", "add", "."], cwd=src, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.com",
            "commit",
            "-q",
            "-m",
            "planted secrets",
        ],
        cwd=src,
        check=True,
    )

    out = tmp_path / "harvest-out"
    config = HarvestConfig(
        repo=str(src),
        out=out,
        log_level="warn",
        llm_enabled=False,
        fail_on_gaps=False,
    )
    result = HarvestPipeline().run(config)

    # (d) harvest still succeeds
    assert result.success, (
        f"Pipeline failed at stage {result.error_stage}: {result.error_message}"
    )

    # (a) raw key/email appear NOWHERE under the output dir (repo/ excluded —
    #     it is the untouched clone of the source, not harvester output).
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        if "repo" in path.relative_to(out).parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert "AKIAIOSFODNN7EXAMPLE" not in text, f"AWS key leaked into {path}"
        assert "alice@example.com" not in text, f"email leaked into {path}"

    # (b) reports/sensitive-findings.json exists with >=2 findings
    findings_json = out / "reports" / "sensitive-findings.json"
    assert findings_json.is_file()
    payload = json.loads(findings_json.read_text(encoding="utf-8"))
    assert payload["count"] >= 2
    kinds = {f["kind"] for f in payload["findings"]}
    assert "aws-access-key" in kinds
    assert "email" in kinds

    # (c) REQUIREMENTS.md carries the rollup line
    requirements = (out / "REQUIREMENTS.md").read_text(encoding="utf-8")
    assert "sensitive value(s)" in requirements
    assert "reports/sensitive-findings.md" in requirements

    assert result.sensitive_findings_count >= 2


@pytest.mark.integration
def test_pipeline_flask_factory_fixture(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """BEAN-089: blueprint prefixes, verb shorthand and factory routes resolve."""
    repo = local_git_repo("python-flask-factory")
    out = tmp_path / "harvest-out"

    result = _run_pipeline(repo, out)

    assert result.success
    contract = json.loads((out / "api-contract.json").read_text())
    ops = {(m.upper(), p) for p, v in contract["paths"].items() for m in v}
    assert ops == {
        ("GET", "/health"),
        ("GET", "/api/items/"),
        ("POST", "/api/items/"),
        ("DELETE", "/api/items/{item_id}"),
    }


@pytest.mark.integration
def test_pipeline_ts_next_contracts_and_fidelity(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """BEAN-063: Next.js route handlers get contracts; fidelity gate passes."""
    from openapi_spec_validator import validate

    repo = local_git_repo("ts-next")
    out = tmp_path / "harvest-out"

    result = _run_pipeline(repo, out)

    assert result.success
    contract = json.loads((out / "api-contract.json").read_text())
    validate(contract)
    get = contract["paths"]["/api/users"]["get"]
    schema = get["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["type"] == "array"
    assert set(schema["items"]["properties"]) == {"id", "name", "email"}
    post = contract["paths"]["/api/users"]["post"]
    assert "201" in post["responses"]
    assert "x-harvester-gap" not in get and "x-harvester-gap" not in post
    coverage = json.loads((out / "reports" / "coverage.json").read_text())
    assert coverage["fidelity"]["all_passed"] is True


@pytest.mark.integration
def test_pipeline_ts_next_screen_with_field_mapping(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """BEAN-064: the UserForm screen lists its fields mapped to API + model."""
    repo = local_git_repo("ts-next")
    out = tmp_path / "harvest-out"
    assert _run_pipeline(repo, out).success

    surfaces = json.loads((out / "surfaces.json").read_text())["surfaces"]
    form = next(s for s in surfaces["screens"] if s["screen_name"] == "UserForm")
    fields = {f["name"]: f for f in form["fields"]}
    assert set(fields) == {"name", "email"}
    assert fields["name"]["required"] is True
    assert "minLength=2" in fields["name"]["validation"]
    assert fields["name"]["bound_model_field"] == "User.name"
    assert fields["name"]["bound_api_field"].startswith("POST /api/users#name")
    assert fields["email"]["bound_model_field"] == "User.email"
    assert any(a["api_ref"] == "POST /api/users" for a in form["actions"])
    assert "/" in form["navigation_targets"]
    coverage = json.loads((out / "reports" / "coverage.json").read_text())
    metric = next(
        m
        for m in coverage["fidelity"]["metrics"]
        if m["name"] == "screen_field_mappings"
    )
    assert metric["applicable"] and metric["percentage"] == 100.0


@pytest.mark.integration
@pytest.mark.parametrize("fixture", ["python-flask", "ts-next"])
def test_fixture_business_rules(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    """BEAN-065: >=3 rules, >=2 kinds, every rule links to a real surface."""
    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo(fixture), out).success
    surfaces = json.loads((out / "surfaces.json").read_text())["surfaces"]
    rules = surfaces["business_rules"]
    assert len(rules) >= 3
    assert len({r["rule_kind"] for r in rules}) >= 2
    names = {
        s["name"]
        for key, group in surfaces.items()
        if key != "business_rules"
        for s in group
    }
    assert all(r["applies_to"] and set(r["applies_to"]) <= names for r in rules)
    assert (out / "beans").glob("BEAN-*.md")


@pytest.mark.integration
def test_pipeline_flask_workflow_fixture(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """BEAN-067: status enum + transition endpoints → inferred and declared workflows."""
    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo("python-flask-workflow"), out).success
    wfs = json.loads((out / "surfaces.json").read_text())["surfaces"]["workflows"]
    inferred = next(w for w in wfs if w["confidence"] == "inferred")
    assert set(inferred["states"]) >= {"DRAFT", "SUBMITTED", "PAID"}
    pairs = {
        (t["from_state"], t["to_state"]): t["trigger_ref"]
        for t in inferred["transitions"]
    }
    assert pairs[("DRAFT", "SUBMITTED")] == "POST /api/orders/<int:order_id>/submit"
    assert pairs[("SUBMITTED", "PAID")] == "POST /api/orders/<int:order_id>/pay"
    table = next(w for w in wfs if w["source_library"] == "transition-table")
    assert len(table["transitions"]) == 5


@pytest.mark.integration
def test_pipeline_xstate_fixture(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo("ts-xstate"), out).success
    wfs = json.loads((out / "surfaces.json").read_text())["surfaces"]["workflows"]
    (wf,) = [w for w in wfs if w["source_library"] == "xstate"]
    assert wf["initial_state"] == "draft" and len(wf["transitions"]) == 5
    assert any(t["guard"] == "hasPaymentMethod" for t in wf["transitions"])


@pytest.mark.integration
def test_pipeline_dotnet_api_contracts(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """ASP.NET controllers get DTO-derived contracts incl. DataAnnotations rules."""
    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo("dotnet-api"), out).success
    contract = json.loads((out / "api-contract.json").read_text())
    post = contract["paths"]["/api/items"]["post"]
    body = post["requestBody"]["content"]["application/json"]["schema"]
    assert set(body["properties"]) == {"Name", "Qty"} and "Name" in body["required"]
    assert "201" in post["responses"] and "400" in post["responses"]
    rules = json.loads((out / "surfaces.json").read_text())["surfaces"][
        "business_rules"
    ]
    exprs = {r["expression"] for r in rules}
    assert any("minimum length 2" in e for e in exprs)
    assert any("minimum value 1" in e or "maximum value 100" in e for e in exprs)


@pytest.mark.integration
@pytest.mark.parametrize("fixture", ["ts-next", "python-flask-workflow"])
def test_features_and_build_manifest(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    """BEAN-069: features/, build-manifest.json, bean `feature:` keys, determinism."""
    import jsonschema

    from repo_mirror_kit.harvester.features import MANIFEST_SCHEMA

    repo = local_git_repo(fixture)
    manifests = []
    for run in ("one", "two"):
        out = tmp_path / run
        assert _run_pipeline(repo, out).success
        manifests.append((out / "build-manifest.json").read_text())
    assert manifests[0] == manifests[1], "manifest must be byte-identical across runs"

    manifest = json.loads(manifests[0])
    jsonschema.validate(manifest, MANIFEST_SCHEMA)
    out = tmp_path / "one"
    assert len(manifest["features"]) >= 2
    assert sorted(manifest["build_order"]["beans"]) == sorted(
        b["id"] for b in manifest["beans"]
    )
    for feat in manifest["features"]:
        assert (out / feat["path"]).is_file()
    for bean in manifest["beans"]:
        text = (out / bean["path"]).read_text()
        assert f"\nfeature: {bean['feature']}\n" in text
    assigned = [b for f in manifest["features"] for b in f["beans"]]
    assert len(assigned) == len(set(assigned)) == len(manifest["beans"])
    req = (out / "REQUIREMENTS.md").read_text()
    assert "## Features (suggested build order)" in req and "features/FEAT-001" in req


@pytest.mark.integration
@pytest.mark.parametrize(
    "fixture", ["python-flask", "python-flask-workflow", "ts-next"]
)
def test_db_design_bundle_for_fixtures(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    """BEAN-072: every detected model appears in executable DDL and JSON Schema."""
    import sqlite3

    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo(fixture), out).success
    surfaces = json.loads((out / "surfaces.json").read_text())["surfaces"]
    models = [m["entity_name"] or m["name"] for m in surfaces["models"]]
    assert models
    db = out / "db-design"
    con = sqlite3.connect(":memory:")
    con.executescript((db / "schema.sql").read_text())
    tables = {
        r[0] for r in con.execute("select name from sqlite_master where type='table'")
    }
    assert len(tables) == len(models)
    for name in models:
        assert (db / "entities" / f"{name}.schema.json").is_file()
    assert (db / "README.md").is_file()


@pytest.mark.integration
def test_screen_specs_for_ts_next(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """BEAN-073: one YAML per detected screen, schema-valid, bindings present."""
    import jsonschema
    import yaml

    from repo_mirror_kit.harvester.generator.screen_specs import SCREEN_SCHEMA

    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo("ts-next"), out).success
    screens = json.loads((out / "surfaces.json").read_text())["surfaces"]["screens"]
    yamls = sorted((out / "screens").glob("*.yaml"))
    assert len(yamls) == len(screens) >= 1
    for path in yamls:
        jsonschema.validate(yaml.safe_load(path.read_text()), SCREEN_SCHEMA)
    form = yaml.safe_load((out / "screens" / "userform.yaml").read_text())
    assert {f["binds_to"]["model"] for f in form["fields"]} == {
        "User.name",
        "User.email",
    }
    assert (
        "```mermaid\nflowchart TD"
        in (out / "screens" / "navigation-map.md").read_text()
    )
    assert "screens/README.md" in (out / "REQUIREMENTS.md").read_text()


@pytest.mark.integration
@pytest.mark.parametrize("fixture", ["ts-next", "python-flask-workflow", "dotnet-api"])
def test_gherkin_for_fixtures_parses_and_traces(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    """BEAN-074: >=1 parseable .feature per feature cluster with scenarios."""
    import re

    from gherkin.parser import Parser

    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo(fixture), out).success
    manifest = json.loads((out / "build-manifest.json").read_text())
    files = sorted((out / "gherkin").glob("*.feature"))
    assert files
    covered = {f.name.split("-")[0] + "-" + f.name.split("-")[1] for f in files}
    with_behavior = {
        b["feature"] for b in manifest["beans"] if b["type"] in ("api", "model")
    }
    assert with_behavior and with_behavior <= covered
    parser = Parser()
    for path in files:
        doc = parser.parse(path.read_text())
        for child in doc["feature"]["children"]:
            sc = child.get("scenario")
            if sc:
                assert any(re.fullmatch(r"@BEAN-\d+", t["name"]) for t in sc["tags"])
    assert "gherkin/" in (out / "REQUIREMENTS.md").read_text()


@pytest.mark.integration
def test_diagrams_for_workflow_and_screen_fixtures(
    local_git_repo: Callable[[str], Path], tmp_path: Path
) -> None:
    """BEAN-075: state diagram for the order workflow; sequence for the form."""
    out = tmp_path / "wf"
    assert _run_pipeline(local_git_repo("python-flask-workflow"), out).success
    state_files = sorted((out / "diagrams").glob("state-*.md"))
    assert state_files
    text = "\n".join(p.read_text() for p in state_files)
    assert "stateDiagram-v2" in text and "SUBMITTED" in text and "PAID" in text
    out2 = tmp_path / "ui"
    assert _run_pipeline(local_git_repo("ts-next"), out2).success
    seq = list((out2 / "diagrams").glob("sequence-*.md"))
    assert seq and "sequenceDiagram" in seq[0].read_text()
    assert "diagrams/README.md" in (out2 / "REQUIREMENTS.md").read_text()


@pytest.mark.integration
@pytest.mark.parametrize("fixture", ["ts-next", "python-flask-workflow", "dotnet-api"])
def test_requirements_md_indexes_every_artifact(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    """BEAN-075/6.5: nothing in the output root is orphaned from REQUIREMENTS.md."""
    out = tmp_path / "harvest-out"
    assert _run_pipeline(local_git_repo(fixture), out).success
    text = (out / "REQUIREMENTS.md").read_text()
    internal = {"repo", "state", "REQUIREMENTS.md", "reports", "surface-map.json"}
    for entry in sorted(out.iterdir()):
        if entry.name in internal:
            continue
        assert entry.name in text, f"{entry.name} is not linked from REQUIREMENTS.md"
    assert "reports/coverage.md" in text and "reports/gaps.md" in text
