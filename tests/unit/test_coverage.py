"""Unit tests for coverage metrics computation, threshold evaluation, and reports."""

from __future__ import annotations

import json
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    StateMgmtSurface,
    SurfaceCollection,
    UIFlowSurface,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.inventory import InventoryResult
from repo_mirror_kit.harvester.reports.coverage import (
    THRESHOLD_APIS,
    THRESHOLD_COMPONENTS,
    THRESHOLD_ENV_VARS,
    THRESHOLD_INTEGRATIONS,
    THRESHOLD_MIDDLEWARE,
    THRESHOLD_MODELS,
    THRESHOLD_ROUTES,
    THRESHOLD_STATE_MGMT,
    THRESHOLD_UI_FLOWS,
    MetricPair,
    compute_metrics,
    evaluate_thresholds,
    generate_coverage_json,
    generate_coverage_markdown,
    write_coverage_reports,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bean(
    number: int,
    surface_type: str,
    title: str = "test",
    skipped: bool = False,
) -> WrittenBean:
    """Create a WrittenBean for testing."""
    bean_id = f"BEAN-{number:03d}"
    return WrittenBean(
        bean_number=number,
        bean_id=bean_id,
        slug=title.lower().replace(" ", "-"),
        surface_type=surface_type,
        title=title,
        path=Path(f"/tmp/beans/{bean_id}-{title}.md"),
        skipped=skipped,
    )


def _make_inventory(total_files: int = 100, total_skipped: int = 10) -> InventoryResult:
    """Create an InventoryResult for testing."""
    return InventoryResult(
        files=[],
        skipped=[],
        total_files=total_files,
        total_size=0,
        total_skipped=total_skipped,
    )


def _make_collection(
    routes: int = 0,
    components: int = 0,
    apis: int = 0,
    models: int = 0,
    auth: int = 0,
    config: int = 0,
    state_mgmt: int = 0,
    middleware: int = 0,
    integrations: int = 0,
    ui_flows: int = 0,
) -> SurfaceCollection:
    """Create a SurfaceCollection with given counts."""
    ref = SourceRef(file_path="src/app.py", start_line=1)
    return SurfaceCollection(
        routes=[
            RouteSurface(
                name=f"route_{i}", path=f"/route/{i}", method="GET", source_refs=[ref]
            )
            for i in range(routes)
        ],
        components=[
            ComponentSurface(name=f"comp_{i}", source_refs=[ref])
            for i in range(components)
        ],
        apis=[
            ApiSurface(
                name=f"api_{i}", method="GET", path=f"/api/{i}", source_refs=[ref]
            )
            for i in range(apis)
        ],
        models=[
            ModelSurface(name=f"model_{i}", source_refs=[ref]) for i in range(models)
        ],
        auth=[AuthSurface(name=f"auth_{i}", source_refs=[ref]) for i in range(auth)],
        config=[
            ConfigSurface(
                name=f"config_{i}", env_var_name=f"CONFIG_{i}", source_refs=[ref]
            )
            for i in range(config)
        ],
        state_mgmt=[
            StateMgmtSurface(
                name=f"store_{i}",
                store_name=f"store_{i}",
                pattern="redux",
                source_refs=[ref],
            )
            for i in range(state_mgmt)
        ],
        middleware=[
            MiddlewareSurface(
                name=f"mw_{i}", middleware_type="express", source_refs=[ref]
            )
            for i in range(middleware)
        ],
        integrations=[
            IntegrationSurface(
                name=f"integ_{i}", integration_type="rest_client", source_refs=[ref]
            )
            for i in range(integrations)
        ],
        ui_flows=[
            UIFlowSurface(name=f"flow_{i}", flow_type="wizard", source_refs=[ref])
            for i in range(ui_flows)
        ],
    )


# ---------------------------------------------------------------------------
# MetricPair tests
# ---------------------------------------------------------------------------


class TestMetricPair:
    def test_percentage_normal(self) -> None:
        pair = MetricPair(total=100, covered=95)
        assert pair.percentage == 95.0

    def test_percentage_zero_total(self) -> None:
        pair = MetricPair(total=0, covered=0)
        assert pair.percentage == 100.0

    def test_percentage_full_coverage(self) -> None:
        pair = MetricPair(total=50, covered=50)
        assert pair.percentage == 100.0

    def test_percentage_zero_covered(self) -> None:
        pair = MetricPair(total=10, covered=0)
        assert pair.percentage == 0.0

    def test_percentage_partial(self) -> None:
        pair = MetricPair(total=3, covered=2)
        assert abs(pair.percentage - 66.666666) < 0.001


# ---------------------------------------------------------------------------
# compute_metrics tests
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_all_surfaces_covered(self) -> None:
        collection = _make_collection(
            routes=3, components=2, apis=4, models=1, auth=1, config=2
        )
        beans = [
            *[_make_bean(i + 1, "route", f"route_{i}") for i in range(3)],
            *[_make_bean(i + 4, "component", f"comp_{i}") for i in range(2)],
            *[_make_bean(i + 6, "api", f"api_{i}") for i in range(4)],
            _make_bean(10, "model", "model_0"),
            _make_bean(11, "auth", "auth_0"),
            *[_make_bean(i + 12, "config", f"config_{i}") for i in range(2)],
        ]
        inventory = _make_inventory(100, 10)

        metrics = compute_metrics(collection, beans, inventory)

        assert metrics.files.total == 110
        assert metrics.files.scanned == 100
        assert metrics.files.skipped == 10
        assert metrics.routes.total == 3
        assert metrics.routes.covered == 3
        assert metrics.shared_components.total == 2
        assert metrics.shared_components.covered == 2
        assert metrics.apis.total == 4
        assert metrics.apis.covered == 4
        assert metrics.models.total == 1
        assert metrics.models.covered == 1
        assert metrics.env_vars.total == 2
        assert metrics.env_vars.covered == 2
        assert metrics.auth_surfaces.total == 1
        assert metrics.auth_surfaces.covered == 1

    def test_no_surfaces(self) -> None:
        collection = _make_collection()
        beans: list[WrittenBean] = []
        inventory = _make_inventory(50, 5)

        metrics = compute_metrics(collection, beans, inventory)

        assert metrics.routes.total == 0
        assert metrics.routes.covered == 0
        assert metrics.apis.total == 0
        assert metrics.models.total == 0

    def test_partial_coverage(self) -> None:
        collection = _make_collection(routes=10, apis=5)
        beans = [_make_bean(i + 1, "route", f"route_{i}") for i in range(8)]
        inventory = _make_inventory()

        metrics = compute_metrics(collection, beans, inventory)

        assert metrics.routes.total == 10
        assert metrics.routes.covered == 8
        assert metrics.apis.total == 5
        assert metrics.apis.covered == 0

    def test_file_metrics(self) -> None:
        collection = _make_collection()
        inventory = _make_inventory(total_files=200, total_skipped=25)

        metrics = compute_metrics(collection, [], inventory)

        assert metrics.files.total == 225
        assert metrics.files.scanned == 200
        assert metrics.files.skipped == 25


# ---------------------------------------------------------------------------
# evaluate_thresholds tests
# ---------------------------------------------------------------------------


class TestEvaluateThresholds:
    def test_all_pass_full_coverage(self) -> None:
        collection = _make_collection(
            routes=10, components=10, apis=10, models=10, config=10
        )
        beans = [
            *[_make_bean(i + 1, "route", f"route_{i}") for i in range(10)],
            *[_make_bean(i + 11, "component", f"comp_{i}") for i in range(10)],
            *[_make_bean(i + 21, "api", f"api_{i}") for i in range(10)],
            *[_make_bean(i + 31, "model", f"model_{i}") for i in range(10)],
            *[_make_bean(i + 41, "config", f"config_{i}") for i in range(10)],
        ]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        assert evaluation.all_passed is True
        assert all(g.passed for g in evaluation.gates)

    def test_all_pass_zero_totals(self) -> None:
        """Zero totals should vacuously pass all gates."""
        collection = _make_collection()
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)

        evaluation = evaluate_thresholds(metrics)

        assert evaluation.all_passed is True
        for gate in evaluation.gates:
            assert gate.passed is True
            assert gate.actual == 100.0

    def test_routes_fail_below_threshold(self) -> None:
        """Routes at 90% should fail the 95% gate."""
        collection = _make_collection(routes=10)
        beans = [_make_bean(i + 1, "route", f"route_{i}") for i in range(9)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        route_gate = next(g for g in evaluation.gates if g.name == "Routes")
        assert route_gate.passed is False
        assert route_gate.actual == 90.0
        assert route_gate.threshold == THRESHOLD_ROUTES
        assert evaluation.all_passed is False

    def test_routes_pass_at_exact_threshold(self) -> None:
        """Routes at exactly 95% should pass."""
        collection = _make_collection(routes=20)
        beans = [_make_bean(i + 1, "route", f"route_{i}") for i in range(19)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        route_gate = next(g for g in evaluation.gates if g.name == "Routes")
        assert route_gate.passed is True
        assert route_gate.actual == 95.0

    def test_components_different_threshold(self) -> None:
        """Components use 85% threshold, not 95%."""
        collection = _make_collection(components=20)
        # 17/20 = 85% -- should pass
        beans = [_make_bean(i + 1, "component", f"comp_{i}") for i in range(17)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        comp_gate = next(g for g in evaluation.gates if g.name == "Components")
        assert comp_gate.passed is True
        assert comp_gate.actual == 85.0
        assert comp_gate.threshold == THRESHOLD_COMPONENTS

    def test_components_fail_below_threshold(self) -> None:
        """Components at 80% should fail the 85% gate."""
        collection = _make_collection(components=10)
        beans = [_make_bean(i + 1, "component", f"comp_{i}") for i in range(8)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        comp_gate = next(g for g in evaluation.gates if g.name == "Components")
        assert comp_gate.passed is False
        assert comp_gate.actual == 80.0

    def test_env_vars_require_100_percent(self) -> None:
        """Env vars require 100% documentation."""
        collection = _make_collection(config=5)
        beans = [_make_bean(i + 1, "config", f"config_{i}") for i in range(4)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        env_gate = next(g for g in evaluation.gates if g.name == "Env Vars")
        assert env_gate.passed is False
        assert env_gate.actual == 80.0
        assert env_gate.threshold == THRESHOLD_ENV_VARS

    def test_env_vars_pass_at_100(self) -> None:
        collection = _make_collection(config=5)
        beans = [_make_bean(i + 1, "config", f"config_{i}") for i in range(5)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        env_gate = next(g for g in evaluation.gates if g.name == "Env Vars")
        assert env_gate.passed is True
        assert env_gate.actual == 100.0

    def test_multiple_gates_fail(self) -> None:
        """Multiple gates can fail simultaneously."""
        collection = _make_collection(routes=10, apis=10, models=10)
        beans: list[WrittenBean] = []  # No beans at all
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)

        evaluation = evaluate_thresholds(metrics)

        assert evaluation.all_passed is False
        failing = [g for g in evaluation.gates if not g.passed]
        assert len(failing) >= 3

    def test_gate_count(self) -> None:
        """Should have exactly 13 gates matching spec section 7.2."""
        collection = _make_collection()
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)

        evaluation = evaluate_thresholds(metrics)

        assert len(evaluation.gates) == 13
        gate_names = {g.name for g in evaluation.gates}
        assert gate_names == {
            "Routes",
            "APIs",
            "Models",
            "Components",
            "Env Vars",
            "State Mgmt",
            "Middleware",
            "Integrations",
            "UI Flows",
            "Build/Deploy",
            "Dependencies",
            "Test Patterns",
            "General Logic",
        }


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------


class TestCoverageJson:
    def test_valid_json(self) -> None:
        collection = _make_collection(routes=5)
        beans = [_make_bean(i + 1, "route", f"route_{i}") for i in range(5)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_json(evaluation)
        data = json.loads(result)

        assert "metrics" in data
        assert "gates" in data
        assert "all_passed" in data

    def test_json_contains_all_metric_categories(self) -> None:
        collection = _make_collection(
            routes=1, components=1, apis=1, models=1, config=1, auth=1
        )
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_json(evaluation)
        data = json.loads(result)

        expected_keys = {
            "files",
            "routes",
            "shared_components",
            "apis",
            "models",
            "env_vars",
            "auth_surfaces",
            "state_mgmt",
            "middleware",
            "integrations",
            "ui_flows",
            "build_deploy",
            "dependencies",
            "test_patterns",
            "general_logic",
        }
        assert set(data["metrics"].keys()) == expected_keys

    def test_json_files_metrics(self) -> None:
        collection = _make_collection()
        inventory = _make_inventory(total_files=100, total_skipped=20)
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_json(evaluation)
        data = json.loads(result)

        files = data["metrics"]["files"]
        assert files["total"] == 120
        assert files["scanned"] == 100
        assert files["skipped"] == 20

    def test_json_routes_naming(self) -> None:
        """Routes metric uses 'with_page_bean' key per spec."""
        collection = _make_collection(routes=3)
        beans = [_make_bean(1, "route", "route_0")]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_json(evaluation)
        data = json.loads(result)

        assert "with_page_bean" in data["metrics"]["routes"]
        assert data["metrics"]["routes"]["total"] == 3
        assert data["metrics"]["routes"]["with_page_bean"] == 1


class TestCoverageMarkdown:
    def test_contains_sections(self) -> None:
        collection = _make_collection(routes=5)
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_markdown(evaluation)

        assert "# Coverage Report" in result
        assert "## File Metrics" in result
        assert "## Surface Coverage" in result
        assert "## Coverage Gates" in result

    def test_contains_pass_fail(self) -> None:
        collection = _make_collection(routes=10)
        beans = [_make_bean(i + 1, "route", f"route_{i}") for i in range(10)]
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_markdown(evaluation)

        assert "PASS" in result
        assert "ALL GATES PASSED" in result

    def test_contains_fail_status(self) -> None:
        collection = _make_collection(routes=10)
        beans: list[WrittenBean] = []
        inventory = _make_inventory()
        metrics = compute_metrics(collection, beans, inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_markdown(evaluation)

        assert "FAIL" in result
        assert "GATES FAILED" in result

    def test_table_rows(self) -> None:
        collection = _make_collection(routes=5, apis=3)
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        result = generate_coverage_markdown(evaluation)

        assert "Routes" in result
        assert "APIs" in result
        assert "Components" in result
        assert "Models" in result
        assert "Env Vars" in result
        assert "Auth Surfaces" in result


class TestWriteCoverageReports:
    def test_writes_both_files(self, tmp_path: Path) -> None:
        collection = _make_collection(routes=2)
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        json_path, md_path = write_coverage_reports(tmp_path, evaluation)

        assert json_path.exists()
        assert md_path.exists()
        assert json_path.name == "coverage.json"
        assert md_path.name == "coverage.md"

    def test_json_is_valid(self, tmp_path: Path) -> None:
        collection = _make_collection(routes=2)
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        json_path, _ = write_coverage_reports(tmp_path, evaluation)

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["all_passed"] is False  # 0/2 routes

    def test_creates_reports_dir(self, tmp_path: Path) -> None:
        collection = _make_collection()
        inventory = _make_inventory()
        metrics = compute_metrics(collection, [], inventory)
        evaluation = evaluate_thresholds(metrics)

        json_path, _ = write_coverage_reports(tmp_path, evaluation)

        assert json_path.parent.name == "reports"
        assert json_path.parent.exists()


# ---------------------------------------------------------------------------
# Threshold constants tests
# ---------------------------------------------------------------------------


class TestThresholdConstants:
    def test_routes_threshold(self) -> None:
        assert THRESHOLD_ROUTES == 95.0

    def test_apis_threshold(self) -> None:
        assert THRESHOLD_APIS == 95.0

    def test_models_threshold(self) -> None:
        assert THRESHOLD_MODELS == 95.0

    def test_components_threshold(self) -> None:
        assert THRESHOLD_COMPONENTS == 85.0

    def test_env_vars_threshold(self) -> None:
        assert THRESHOLD_ENV_VARS == 100.0

    def test_state_mgmt_threshold(self) -> None:
        assert THRESHOLD_STATE_MGMT == 80.0

    def test_middleware_threshold(self) -> None:
        assert THRESHOLD_MIDDLEWARE == 80.0

    def test_integrations_threshold(self) -> None:
        assert THRESHOLD_INTEGRATIONS == 85.0

    def test_ui_flows_threshold(self) -> None:
        assert THRESHOLD_UI_FLOWS == 75.0
