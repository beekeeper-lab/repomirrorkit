"""Unit tests for the SQL/ORM data layer detector."""

from __future__ import annotations

from repo_mirror_kit.harvester.detectors.base import (
    Detector,
    clear_registry,
    get_all_detectors,
    run_detection,
)
from repo_mirror_kit.harvester.detectors.data import DataDetector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(
            path=p,
            size=100,
            extension="." + p.rsplit(".", 1)[-1] if "." in p.rsplit("/", 1)[-1] else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=100 * len(files),
        total_skipped=0,
    )


def _make_detector() -> DataDetector:
    """Create a fresh DataDetector instance."""
    return DataDetector()


# ---------------------------------------------------------------------------
# Interface conformance
# ---------------------------------------------------------------------------


class TestDataDetectorInterface:
    """Verify DataDetector implements the Detector interface."""

    def test_is_detector_subclass(self) -> None:
        assert issubclass(DataDetector, Detector)

    def test_instance_is_detector(self) -> None:
        detector = _make_detector()
        assert isinstance(detector, Detector)

    def test_detect_returns_list(self) -> None:
        detector = _make_detector()
        result = detector.detect(_make_inventory([]))
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Prisma detection
# ---------------------------------------------------------------------------


class TestPrismaDetection:
    """Tests for Prisma ORM detection."""

    def test_prisma_schema_file(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(["prisma/schema.prisma", "package.json"])
        )
        prisma_signals = [s for s in signals if s.stack_name == "prisma"]
        assert len(prisma_signals) == 1
        assert "prisma/schema.prisma" in prisma_signals[0].evidence
        assert prisma_signals[0].confidence >= 0.7

    def test_prisma_schema_with_package_json(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(["prisma/schema.prisma", "package.json"])
        )
        prisma_signals = [s for s in signals if s.stack_name == "prisma"]
        assert len(prisma_signals) == 1
        assert "package.json" in prisma_signals[0].evidence
        assert prisma_signals[0].confidence >= 0.9

    def test_package_json_alone_low_prisma_confidence(self) -> None:
        """package.json alone gives a weak Prisma signal."""
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["package.json"]))
        prisma_signals = [s for s in signals if s.stack_name == "prisma"]
        assert len(prisma_signals) == 1
        assert prisma_signals[0].confidence < 0.3

    def test_no_prisma_without_indicators(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/app.py"]))
        prisma_signals = [s for s in signals if s.stack_name == "prisma"]
        assert len(prisma_signals) == 0


# ---------------------------------------------------------------------------
# SQLAlchemy detection
# ---------------------------------------------------------------------------


class TestSQLAlchemyDetection:
    """Tests for SQLAlchemy ORM detection."""

    def test_sqlalchemy_with_models_and_deps(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(["pyproject.toml", "src/app/models.py"])
        )
        sa_signals = [s for s in signals if s.stack_name == "sqlalchemy"]
        assert len(sa_signals) == 1
        assert sa_signals[0].confidence >= 0.5

    def test_sqlalchemy_with_requirements_txt(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(["requirements.txt", "app/models.py"])
        )
        sa_signals = [s for s in signals if s.stack_name == "sqlalchemy"]
        assert len(sa_signals) == 1

    def test_sqlalchemy_with_setup_py(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["setup.py", "myapp/model.py"]))
        sa_signals = [s for s in signals if s.stack_name == "sqlalchemy"]
        assert len(sa_signals) == 1

    def test_no_sqlalchemy_without_model_file(self) -> None:
        """Dependency file alone is not enough for SQLAlchemy."""
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["pyproject.toml"]))
        sa_signals = [s for s in signals if s.stack_name == "sqlalchemy"]
        assert len(sa_signals) == 0

    def test_no_sqlalchemy_without_dep_file(self) -> None:
        """Model file alone is not enough for SQLAlchemy."""
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/models.py"]))
        sa_signals = [s for s in signals if s.stack_name == "sqlalchemy"]
        assert len(sa_signals) == 0


# ---------------------------------------------------------------------------
# Alembic detection
# ---------------------------------------------------------------------------


class TestAlembicDetection:
    """Tests for Alembic migration detection."""

    def test_alembic_directory(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["alembic/versions/001_init.py"]))
        alembic_signals = [s for s in signals if s.stack_name == "alembic"]
        assert len(alembic_signals) == 1
        assert alembic_signals[0].confidence >= 0.5

    def test_alembic_ini(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["alembic.ini"]))
        alembic_signals = [s for s in signals if s.stack_name == "alembic"]
        assert len(alembic_signals) == 1
        assert alembic_signals[0].confidence >= 0.4

    def test_alembic_full_setup(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "alembic.ini",
                    "alembic/env.py",
                    "alembic/versions/001_init.py",
                ]
            )
        )
        alembic_signals = [s for s in signals if s.stack_name == "alembic"]
        assert len(alembic_signals) == 1
        assert alembic_signals[0].confidence >= 0.9

    def test_no_alembic_without_indicators(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/app.py"]))
        alembic_signals = [s for s in signals if s.stack_name == "alembic"]
        assert len(alembic_signals) == 0


# ---------------------------------------------------------------------------
# Entity Framework detection
# ---------------------------------------------------------------------------


class TestEntityFrameworkDetection:
    """Tests for Entity Framework detection."""

    def test_ef_csproj_and_migrations(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "MyApp/MyApp.csproj",
                    "MyApp/Migrations/20230101_Init.cs",
                ]
            )
        )
        ef_signals = [s for s in signals if s.stack_name == "entity-framework"]
        assert len(ef_signals) == 1
        assert ef_signals[0].confidence >= 0.7

    def test_ef_csproj_only(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["MyApp/MyApp.csproj"]))
        ef_signals = [s for s in signals if s.stack_name == "entity-framework"]
        assert len(ef_signals) == 1
        assert ef_signals[0].confidence >= 0.3

    def test_ef_migrations_only(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["Migrations/20230101_Init.cs"]))
        ef_signals = [s for s in signals if s.stack_name == "entity-framework"]
        assert len(ef_signals) == 1
        assert ef_signals[0].confidence >= 0.3

    def test_no_ef_without_indicators(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/Program.cs"]))
        ef_signals = [s for s in signals if s.stack_name == "entity-framework"]
        assert len(ef_signals) == 0


# ---------------------------------------------------------------------------
# Flyway detection
# ---------------------------------------------------------------------------


class TestFlywayDetection:
    """Tests for Flyway migration detection."""

    def test_flyway_conf(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["flyway.conf"]))
        flyway_signals = [s for s in signals if s.stack_name == "flyway"]
        assert len(flyway_signals) == 1
        assert flyway_signals[0].confidence >= 0.5

    def test_flyway_sql_dir(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["sql/V1__init.sql"]))
        flyway_signals = [s for s in signals if s.stack_name == "flyway"]
        assert len(flyway_signals) == 1

    def test_flyway_db_migration_dir(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["db/migration/V1__init.sql"]))
        flyway_signals = [s for s in signals if s.stack_name == "flyway"]
        assert len(flyway_signals) == 1

    def test_flyway_full_setup(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "flyway.conf",
                    "sql/V1__init.sql",
                ]
            )
        )
        flyway_signals = [s for s in signals if s.stack_name == "flyway"]
        assert len(flyway_signals) == 1
        assert flyway_signals[0].confidence >= 0.8

    def test_no_flyway_without_indicators(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/Main.java"]))
        flyway_signals = [s for s in signals if s.stack_name == "flyway"]
        assert len(flyway_signals) == 0


# ---------------------------------------------------------------------------
# Liquibase detection
# ---------------------------------------------------------------------------


class TestLiquibaseDetection:
    """Tests for Liquibase migration detection."""

    def test_liquibase_properties(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["liquibase.properties"]))
        lb_signals = [s for s in signals if s.stack_name == "liquibase"]
        assert len(lb_signals) == 1
        assert lb_signals[0].confidence >= 0.5

    def test_liquibase_changelog_dir(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["db/changelog/changes.xml"]))
        lb_signals = [s for s in signals if s.stack_name == "liquibase"]
        assert len(lb_signals) == 1

    def test_liquibase_full_setup(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "liquibase.properties",
                    "db/changelog/changes.xml",
                ]
            )
        )
        lb_signals = [s for s in signals if s.stack_name == "liquibase"]
        assert len(lb_signals) == 1
        assert lb_signals[0].confidence >= 0.8

    def test_no_liquibase_without_indicators(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/Main.java"]))
        lb_signals = [s for s in signals if s.stack_name == "liquibase"]
        assert len(lb_signals) == 0


# ---------------------------------------------------------------------------
# Plain SQL migrations detection
# ---------------------------------------------------------------------------


class TestSQLMigrationsDetection:
    """Tests for plain SQL migration detection."""

    def test_migrations_dir_with_sql(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "migrations/001_create_users.sql",
                    "migrations/002_add_email.sql",
                ]
            )
        )
        sql_signals = [s for s in signals if s.stack_name == "sql-migrations"]
        assert len(sql_signals) == 1
        assert sql_signals[0].confidence >= 0.5

    def test_migration_singular_dir(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["migration/001_init.sql"]))
        sql_signals = [s for s in signals if s.stack_name == "sql-migrations"]
        assert len(sql_signals) == 1

    def test_orm_model_ts_files(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/user.model.ts"]))
        sql_signals = [s for s in signals if s.stack_name == "sql-migrations"]
        assert len(sql_signals) == 1
        assert "src/user.model.ts" in sql_signals[0].evidence

    def test_orm_model_js_files(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/user.model.js"]))
        sql_signals = [s for s in signals if s.stack_name == "sql-migrations"]
        assert len(sql_signals) == 1

    def test_no_sql_migrations_without_indicators(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/app.py", "src/utils.py"]))
        sql_signals = [s for s in signals if s.stack_name == "sql-migrations"]
        assert len(sql_signals) == 0


# ---------------------------------------------------------------------------
# Signal includes tool names
# ---------------------------------------------------------------------------


class TestSignalToolNames:
    """Verify signal stack_name includes specific tool names."""

    def test_prisma_tool_name(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["prisma/schema.prisma"]))
        tool_names = {s.stack_name for s in signals}
        assert "prisma" in tool_names

    def test_alembic_tool_name(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["alembic.ini"]))
        tool_names = {s.stack_name for s in signals}
        assert "alembic" in tool_names

    def test_ef_tool_name(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["MyApp/Migrations/Init.cs"]))
        tool_names = {s.stack_name for s in signals}
        assert "entity-framework" in tool_names


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Tests for confidence scoring based on evidence strength."""

    def test_more_evidence_higher_confidence(self) -> None:
        """Additional indicators should increase confidence."""
        detector = _make_detector()

        # Alembic with only ini
        signals_partial = detector.detect(_make_inventory(["alembic.ini"]))
        alembic_partial = [s for s in signals_partial if s.stack_name == "alembic"]

        # Alembic with ini and directory
        signals_full = detector.detect(
            _make_inventory(["alembic.ini", "alembic/versions/001.py"])
        )
        alembic_full = [s for s in signals_full if s.stack_name == "alembic"]

        assert alembic_full[0].confidence > alembic_partial[0].confidence

    def test_confidence_capped_at_one(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "alembic.ini",
                    "alembic/env.py",
                    "alembic/versions/001.py",
                ]
            )
        )
        for signal in signals:
            assert signal.confidence <= 1.0

    def test_all_confidences_valid_range(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "prisma/schema.prisma",
                    "package.json",
                    "alembic.ini",
                    "alembic/versions/001.py",
                    "pyproject.toml",
                    "src/models.py",
                    "MyApp/MyApp.csproj",
                    "MyApp/Migrations/Init.cs",
                    "flyway.conf",
                    "sql/V1__init.sql",
                    "liquibase.properties",
                    "db/changelog/changes.xml",
                    "migrations/001_init.sql",
                ]
            )
        )
        for signal in signals:
            assert 0.0 <= signal.confidence <= 1.0


# ---------------------------------------------------------------------------
# No data repo
# ---------------------------------------------------------------------------


class TestNoDataRepo:
    """Ensure a project with no data layer produces no signals."""

    def test_empty_inventory(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory([]))
        assert signals == []

    def test_frontend_only_project(self) -> None:
        detector = _make_detector()
        paths = [
            "src/App.tsx",
            "src/index.tsx",
            "src/components/Header.tsx",
            "vite.config.ts",
        ]
        signals = detector.detect(_make_inventory(paths))
        # Should have no high-confidence data signals
        data_stacks = {
            "prisma",
            "sqlalchemy",
            "alembic",
            "entity-framework",
            "flyway",
            "liquibase",
            "sql-migrations",
        }
        high_signals = [
            s for s in signals if s.stack_name in data_stacks and s.confidence >= 0.3
        ]
        assert len(high_signals) == 0

    def test_plain_python_project(self) -> None:
        detector = _make_detector()
        paths = [
            "pyproject.toml",
            "src/mylib/__init__.py",
            "src/mylib/utils.py",
            "tests/test_utils.py",
        ]
        signals = detector.detect(_make_inventory(paths))
        # No model file means no SQLAlchemy detection
        sa_signals = [s for s in signals if s.stack_name == "sqlalchemy"]
        assert len(sa_signals) == 0


# ---------------------------------------------------------------------------
# Multi-data-tool repo
# ---------------------------------------------------------------------------


class TestMultiToolRepo:
    """Ensure multiple data tools can be detected simultaneously."""

    def test_prisma_and_sql_migrations(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "prisma/schema.prisma",
                    "package.json",
                    "migrations/001_init.sql",
                ]
            )
        )
        tool_names = {s.stack_name for s in signals}
        assert "prisma" in tool_names
        assert "sql-migrations" in tool_names

    def test_sqlalchemy_and_alembic_together(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(
                [
                    "pyproject.toml",
                    "src/app/models.py",
                    "alembic.ini",
                    "alembic/versions/001_init.py",
                ]
            )
        )
        tool_names = {s.stack_name for s in signals}
        assert "sqlalchemy" in tool_names
        assert "alembic" in tool_names


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestDataDetectorRegistration:
    """Verify the DataDetector registers itself on module import."""

    def setup_method(self) -> None:
        clear_registry()

    def teardown_method(self) -> None:
        clear_registry()

    def test_detector_in_registry_after_import(self) -> None:
        clear_registry()
        from repo_mirror_kit.harvester.detectors import data as data_mod

        data_mod._create_and_register()
        detectors = get_all_detectors()
        data_detectors = [d for d in detectors if isinstance(d, DataDetector)]
        assert len(data_detectors) >= 1

    def test_run_detection_includes_data(self) -> None:
        clear_registry()
        from repo_mirror_kit.harvester.detectors import data as data_mod

        data_mod._create_and_register()

        inventory = _make_inventory(
            [
                "prisma/schema.prisma",
                "package.json",
            ]
        )
        profile = run_detection(inventory)
        assert "prisma" in profile.stacks
        assert profile.stacks["prisma"] >= 0.3
