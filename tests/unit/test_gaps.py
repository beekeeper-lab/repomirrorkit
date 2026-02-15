"""Unit tests for gap hunt queries and gap report generation."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ConfigSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.reports.gaps import (
    GapEntry,
    GapReport,
    find_apis_without_description,
    find_auth_checks_without_bean,
    find_beans_missing_acceptance_criteria,
    find_env_vars_not_in_report,
    find_models_referenced_but_undocumented,
    find_routes_without_bean,
    generate_gaps_markdown,
    run_all_gap_queries,
    write_gaps_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_REF = SourceRef(file_path="src/app.py", start_line=1)


def _make_bean(
    number: int,
    surface_type: str,
    title: str,
    *,
    skipped: bool = False,
    content: str | None = None,
    tmp_path: Path | None = None,
) -> WrittenBean:
    """Create a WrittenBean for testing, optionally with file content."""
    bean_id = f"BEAN-{number:03d}"
    if tmp_path is not None:
        path = tmp_path / f"{bean_id}-{title}.md"
        if content is not None:
            path.write_text(content, encoding="utf-8")
    else:
        path = Path(f"/nonexistent/{bean_id}-{title}.md")
    return WrittenBean(
        bean_number=number,
        bean_id=bean_id,
        slug=title.lower().replace(" ", "-"),
        surface_type=surface_type,
        title=title,
        path=path,
        skipped=skipped,
    )


def _make_collection(
    routes: list[RouteSurface] | None = None,
    apis: list[ApiSurface] | None = None,
    models: list[ModelSurface] | None = None,
    auth: list[AuthSurface] | None = None,
    config: list[ConfigSurface] | None = None,
) -> SurfaceCollection:
    """Create a SurfaceCollection with given surfaces."""
    return SurfaceCollection(
        routes=routes or [],
        components=[],
        apis=apis or [],
        models=models or [],
        auth=auth or [],
        config=config or [],
    )


# ---------------------------------------------------------------------------
# find_routes_without_bean tests
# ---------------------------------------------------------------------------


class TestFindRoutesWithoutBean:
    def test_no_routes(self) -> None:
        collection = _make_collection()
        entries = find_routes_without_bean(collection, [])
        assert entries == []

    def test_all_routes_covered(self) -> None:
        collection = _make_collection(
            routes=[
                RouteSurface(name="home", path="/", method="GET", source_refs=[_REF]),
                RouteSurface(
                    name="about", path="/about", method="GET", source_refs=[_REF]
                ),
            ]
        )
        beans = [
            _make_bean(1, "route", "home"),
            _make_bean(2, "route", "about"),
        ]
        entries = find_routes_without_bean(collection, beans)
        assert entries == []

    def test_uncovered_routes(self) -> None:
        collection = _make_collection(
            routes=[
                RouteSurface(name="home", path="/", method="GET", source_refs=[_REF]),
                RouteSurface(
                    name="about", path="/about", method="GET", source_refs=[_REF]
                ),
            ]
        )
        beans = [_make_bean(1, "route", "home")]

        entries = find_routes_without_bean(collection, beans)

        assert len(entries) == 1
        assert entries[0].category == "Routes with no bean"
        assert "about" in entries[0].description

    def test_file_path_included(self) -> None:
        ref = SourceRef(file_path="src/routes.py", start_line=10)
        collection = _make_collection(
            routes=[
                RouteSurface(
                    name="login", path="/login", method="POST", source_refs=[ref]
                )
            ]
        )

        entries = find_routes_without_bean(collection, [])

        assert entries[0].file_path == "src/routes.py"

    def test_no_source_refs_uses_unknown(self) -> None:
        collection = _make_collection(
            routes=[
                RouteSurface(
                    name="orphan", path="/orphan", method="GET", source_refs=[]
                )
            ]
        )

        entries = find_routes_without_bean(collection, [])

        assert entries[0].file_path == "unknown"


# ---------------------------------------------------------------------------
# find_beans_missing_acceptance_criteria tests
# ---------------------------------------------------------------------------


class TestFindBeansMissingAcceptanceCriteria:
    def test_bean_with_criteria(self, tmp_path: Path) -> None:
        content = "# Test\n\n## Acceptance criteria\n\n- [ ] Must work\n"
        bean = _make_bean(1, "route", "test", content=content, tmp_path=tmp_path)

        entries = find_beans_missing_acceptance_criteria([bean])

        assert entries == []

    def test_bean_without_criteria(self, tmp_path: Path) -> None:
        content = "# Test\n\nNo criteria here.\n"
        bean = _make_bean(1, "route", "test", content=content, tmp_path=tmp_path)

        entries = find_beans_missing_acceptance_criteria([bean])

        assert len(entries) == 1
        assert entries[0].category == "Beans missing acceptance criteria"
        assert "BEAN-001" in entries[0].description

    def test_skipped_beans_ignored(self, tmp_path: Path) -> None:
        bean = _make_bean(1, "route", "test", skipped=True, tmp_path=tmp_path)

        entries = find_beans_missing_acceptance_criteria([bean])

        assert entries == []

    def test_nonexistent_file_ignored(self) -> None:
        bean = _make_bean(1, "route", "ghost")  # No file created

        entries = find_beans_missing_acceptance_criteria([bean])

        assert entries == []

    def test_multiple_beans_mixed(self, tmp_path: Path) -> None:
        good = _make_bean(
            1,
            "route",
            "good",
            content="# Good\n- [ ] Has criteria\n",
            tmp_path=tmp_path,
        )
        bad = _make_bean(
            2,
            "api",
            "bad",
            content="# Bad\nNo criteria\n",
            tmp_path=tmp_path,
        )

        entries = find_beans_missing_acceptance_criteria([good, bad])

        assert len(entries) == 1
        assert "BEAN-002" in entries[0].description


# ---------------------------------------------------------------------------
# find_apis_without_description tests
# ---------------------------------------------------------------------------


class TestFindApisWithoutDescription:
    def test_no_apis(self) -> None:
        collection = _make_collection()
        entries = find_apis_without_description(collection)
        assert entries == []

    def test_api_with_schemas(self) -> None:
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="create_user",
                    method="POST",
                    path="/api/users",
                    source_refs=[_REF],
                    request_schema={"type": "object"},
                    response_schema={"type": "object"},
                )
            ]
        )

        entries = find_apis_without_description(collection)

        assert entries == []

    def test_api_with_only_request_schema(self) -> None:
        """Having at least one schema is enough."""
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="get_users",
                    method="GET",
                    path="/api/users",
                    source_refs=[_REF],
                    request_schema={"type": "object"},
                )
            ]
        )

        entries = find_apis_without_description(collection)

        assert entries == []

    def test_api_without_schemas(self) -> None:
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="delete_user",
                    method="DELETE",
                    path="/api/users/{id}",
                    source_refs=[_REF],
                )
            ]
        )

        entries = find_apis_without_description(collection)

        assert len(entries) == 1
        assert entries[0].category == "APIs with no request/response description"
        assert "delete_user" in entries[0].description

    def test_multiple_undocumented_apis(self) -> None:
        collection = _make_collection(
            apis=[
                ApiSurface(name="api1", method="GET", path="/1", source_refs=[_REF]),
                ApiSurface(name="api2", method="POST", path="/2", source_refs=[_REF]),
            ]
        )

        entries = find_apis_without_description(collection)

        assert len(entries) == 2


# ---------------------------------------------------------------------------
# find_models_referenced_but_undocumented tests
# ---------------------------------------------------------------------------


class TestFindModelsReferencedButUndocumented:
    def test_no_models(self) -> None:
        collection = _make_collection()
        entries = find_models_referenced_but_undocumented(collection, [])
        assert entries == []

    def test_referenced_model_documented(self) -> None:
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="get_user",
                    method="GET",
                    path="/api/users",
                    source_refs=[_REF],
                    response_schema={"$ref": "#/definitions/User"},
                )
            ],
            models=[ModelSurface(name="User", source_refs=[_REF])],
        )
        beans = [_make_bean(1, "model", "User")]

        entries = find_models_referenced_but_undocumented(collection, beans)

        assert entries == []

    def test_referenced_model_undocumented(self) -> None:
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="get_order",
                    method="GET",
                    path="/api/orders",
                    source_refs=[_REF],
                    response_schema={"$ref": "#/definitions/Order"},
                )
            ],
            models=[ModelSurface(name="Order", source_refs=[_REF])],
        )
        beans: list[WrittenBean] = []

        entries = find_models_referenced_but_undocumented(collection, beans)

        assert len(entries) == 1
        assert entries[0].category == "Models referenced by APIs but not documented"
        assert "Order" in entries[0].description

    def test_reference_to_unknown_model_ignored(self) -> None:
        """Models not in the SurfaceCollection are ignored."""
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="get_item",
                    method="GET",
                    path="/api/items",
                    source_refs=[_REF],
                    response_schema={"$ref": "#/definitions/Widget"},
                )
            ],
        )

        entries = find_models_referenced_but_undocumented(collection, [])

        assert entries == []

    def test_nested_refs_found(self) -> None:
        collection = _make_collection(
            apis=[
                ApiSurface(
                    name="get_complex",
                    method="GET",
                    path="/api/complex",
                    source_refs=[_REF],
                    response_schema={
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"$ref": "#/definitions/Item"},
                            }
                        },
                    },
                )
            ],
            models=[ModelSurface(name="Item", source_refs=[_REF])],
        )

        entries = find_models_referenced_but_undocumented(collection, [])

        assert len(entries) == 1
        assert "Item" in entries[0].description


# ---------------------------------------------------------------------------
# find_env_vars_not_in_report tests
# ---------------------------------------------------------------------------


class TestFindEnvVarsNotInReport:
    def test_no_config_surfaces(self) -> None:
        collection = _make_collection()
        entries = find_env_vars_not_in_report(collection, [])
        assert entries == []

    def test_all_covered(self) -> None:
        collection = _make_collection(
            config=[
                ConfigSurface(
                    name="DB_HOST", env_var_name="DB_HOST", source_refs=[_REF]
                ),
            ]
        )
        beans = [_make_bean(1, "config", "DB_HOST")]

        entries = find_env_vars_not_in_report(collection, beans)

        assert entries == []

    def test_uncovered_env_var(self) -> None:
        collection = _make_collection(
            config=[
                ConfigSurface(
                    name="SECRET_KEY", env_var_name="SECRET_KEY", source_refs=[_REF]
                ),
            ]
        )

        entries = find_env_vars_not_in_report(collection, [])

        assert len(entries) == 1
        assert entries[0].category == "Env vars referenced but not in envvar report"
        assert "SECRET_KEY" in entries[0].description


# ---------------------------------------------------------------------------
# find_auth_checks_without_bean tests
# ---------------------------------------------------------------------------


class TestFindAuthChecksWithoutBean:
    def test_no_auth_surfaces(self) -> None:
        collection = _make_collection()
        entries = find_auth_checks_without_bean(collection, [])
        assert entries == []

    def test_covered_auth(self) -> None:
        collection = _make_collection(
            auth=[AuthSurface(name="jwt_auth", source_refs=[_REF])]
        )
        beans = [_make_bean(1, "auth", "jwt_auth")]

        entries = find_auth_checks_without_bean(collection, beans)

        assert entries == []

    def test_uncovered_auth(self) -> None:
        collection = _make_collection(
            auth=[AuthSurface(name="rbac", source_refs=[_REF])]
        )

        entries = find_auth_checks_without_bean(collection, [])

        assert len(entries) == 1
        assert entries[0].category == "Auth checks present but no auth bean"
        assert "rbac" in entries[0].description


# ---------------------------------------------------------------------------
# run_all_gap_queries tests
# ---------------------------------------------------------------------------


class TestRunAllGapQueries:
    def test_empty_inputs(self) -> None:
        collection = _make_collection()
        report = run_all_gap_queries(collection, [])

        assert report.total_gaps == 0

    def test_combines_all_queries(self) -> None:
        collection = _make_collection(
            routes=[
                RouteSurface(name="r1", path="/r1", method="GET", source_refs=[_REF])
            ],
            apis=[ApiSurface(name="a1", method="GET", path="/a1", source_refs=[_REF])],
            config=[ConfigSurface(name="c1", env_var_name="C1", source_refs=[_REF])],
            auth=[AuthSurface(name="auth1", source_refs=[_REF])],
        )

        report = run_all_gap_queries(collection, [])

        assert report.total_gaps >= 4  # At least one per category
        categories = {e.category for e in report.entries}
        assert "Routes with no bean" in categories
        assert "APIs with no request/response description" in categories
        assert "Env vars referenced but not in envvar report" in categories
        assert "Auth checks present but no auth bean" in categories


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------


class TestGapsMarkdown:
    def test_no_gaps(self) -> None:
        report = GapReport(entries=[])

        result = generate_gaps_markdown(report)

        assert "# Gap Analysis Report" in result
        assert "Total gaps found: 0" in result
        assert "No gaps found" in result

    def test_with_gaps(self) -> None:
        entries = [
            GapEntry(
                category="Routes with no bean",
                description="Route 'home' has no bean",
                file_path="src/routes.py",
                recommended_action="Create a page bean",
            ),
            GapEntry(
                category="Routes with no bean",
                description="Route 'about' has no bean",
                file_path="src/routes.py",
                recommended_action="Create a page bean",
            ),
        ]
        report = GapReport(entries=entries)

        result = generate_gaps_markdown(report)

        assert "Total gaps found: 2" in result
        assert "## Routes with no bean" in result
        assert "Route 'home'" in result
        assert "`src/routes.py`" in result

    def test_multiple_categories(self) -> None:
        entries = [
            GapEntry(
                category="Routes with no bean",
                description="Route gap",
                file_path="a.py",
                recommended_action="Fix route",
            ),
            GapEntry(
                category="Auth checks present but no auth bean",
                description="Auth gap",
                file_path="b.py",
                recommended_action="Fix auth",
            ),
        ]
        report = GapReport(entries=entries)

        result = generate_gaps_markdown(report)

        assert "## Routes with no bean" in result
        assert "## Auth checks present but no auth bean" in result


class TestWriteGapsReport:
    def test_writes_file(self, tmp_path: Path) -> None:
        report = GapReport(entries=[])

        md_path = write_gaps_report(tmp_path, report)

        assert md_path.exists()
        assert md_path.name == "gaps.md"
        assert md_path.parent.name == "reports"

    def test_creates_reports_dir(self, tmp_path: Path) -> None:
        report = GapReport(entries=[])

        write_gaps_report(tmp_path, report)

        assert (tmp_path / "reports").is_dir()

    def test_content_matches_generation(self, tmp_path: Path) -> None:
        entries = [
            GapEntry(
                category="Test category",
                description="A gap",
                file_path="x.py",
                recommended_action="Fix it",
            ),
        ]
        report = GapReport(entries=entries)

        md_path = write_gaps_report(tmp_path, report)

        content = md_path.read_text(encoding="utf-8")
        expected = generate_gaps_markdown(report)
        assert content == expected


# ---------------------------------------------------------------------------
# GapEntry and GapReport data model tests
# ---------------------------------------------------------------------------


class TestGapDataModels:
    def test_gap_entry_fields(self) -> None:
        entry = GapEntry(
            category="cat",
            description="desc",
            file_path="path.py",
            recommended_action="do something",
        )
        assert entry.category == "cat"
        assert entry.description == "desc"
        assert entry.file_path == "path.py"
        assert entry.recommended_action == "do something"

    def test_gap_report_total_gaps(self) -> None:
        entries = [
            GapEntry("a", "b", "c", "d"),
            GapEntry("e", "f", "g", "h"),
        ]
        report = GapReport(entries=entries)
        assert report.total_gaps == 2

    def test_gap_report_empty(self) -> None:
        report = GapReport(entries=[])
        assert report.total_gaps == 0
