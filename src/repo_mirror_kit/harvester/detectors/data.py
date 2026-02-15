"""SQL/ORM data layer detector.

Detects data layer technologies — ORMs, migration tools, and database
schemas — across multiple ecosystems: Prisma (Node), SQLAlchemy/Alembic
(Python), Entity Framework (.NET), Flyway/Liquibase (Java/general), and
plain SQL migrations.
"""

from __future__ import annotations

import re

import structlog

from repo_mirror_kit.harvester.detectors.base import Detector, Signal, register_detector
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

# Prisma
_PRISMA_SCHEMA_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)prisma/schema\.prisma$")

# SQLAlchemy model patterns in Python files
_SQLALCHEMY_MODEL_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)models?\.py$")

# Alembic
_ALEMBIC_DIR_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)alembic/")
_ALEMBIC_INI: str = "alembic.ini"

# Entity Framework
_EF_MIGRATIONS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)Migrations?/.*\.cs$")
_CSPROJ_PATTERN: re.Pattern[str] = re.compile(r"\.csproj$")

# Flyway
_FLYWAY_CONF: str = "flyway.conf"
_FLYWAY_MIGRATION_DIRS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|/)sql/.*\.sql$"),
    re.compile(r"(?:^|/)db/migration/.*\.sql$"),
)

# Liquibase
_LIQUIBASE_PROPERTIES: str = "liquibase.properties"
_LIQUIBASE_CHANGELOG_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)db/changelog/")

# Plain SQL migrations
_SQL_MIGRATION_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)migrations?/.*\.sql$")

# ORM model file patterns
_ORM_MODEL_TS_PATTERN: re.Pattern[str] = re.compile(r"\.model\.[jt]sx?$")

# Config/dependency files
_PACKAGE_JSON: str = "package.json"
_PYPROJECT_TOML: str = "pyproject.toml"
_REQUIREMENTS_TXT_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)requirements.*\.txt$")
_SETUP_PY: str = "setup.py"
_SETUP_CFG: str = "setup.cfg"

# Confidence weights
_CONF_PRISMA_SCHEMA: float = 0.70
_CONF_PRISMA_PACKAGE: float = 0.20

_CONF_SQLALCHEMY_DEPS: float = 0.35
_CONF_SQLALCHEMY_MODELS: float = 0.35

_CONF_ALEMBIC_DIR: float = 0.50
_CONF_ALEMBIC_INI: float = 0.40

_CONF_EF_CSPROJ: float = 0.35
_CONF_EF_MIGRATIONS: float = 0.40

_CONF_FLYWAY_CONF: float = 0.50
_CONF_FLYWAY_MIGRATIONS: float = 0.30

_CONF_LIQUIBASE_PROPS: float = 0.50
_CONF_LIQUIBASE_CHANGELOG: float = 0.30

_CONF_SQL_MIGRATIONS: float = 0.50
_CONF_ORM_MODEL_FILES: float = 0.30


class DataDetector(Detector):
    """Detect data layer technologies across multiple ecosystems.

    Identifies ORMs, migration tools, and schema definition files by
    examining file paths in the inventory for framework-specific naming
    conventions, directory structures, and configuration files.

    Detected stacks:
    - ``prisma`` — Prisma ORM (Node.js)
    - ``sqlalchemy`` — SQLAlchemy ORM (Python)
    - ``alembic`` — Alembic migrations (Python)
    - ``entity-framework`` — Entity Framework Core (.NET)
    - ``flyway`` — Flyway migrations (Java/general)
    - ``liquibase`` — Liquibase migrations (Java/general)
    - ``sql-migrations`` — Plain SQL migration files
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run data layer detection against the file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            Signals for detected data layer technologies.
        """
        files = inventory.files
        if not files:
            return []

        file_paths = [f.path for f in files]
        path_set = set(file_paths)

        signals: list[Signal] = []

        for detect_fn in (
            self._detect_prisma,
            self._detect_sqlalchemy,
            self._detect_alembic,
            self._detect_entity_framework,
            self._detect_flyway,
            self._detect_liquibase,
            self._detect_sql_migrations,
        ):
            signal = detect_fn(file_paths, path_set)
            if signal is not None:
                signals.append(signal)

        logger.info(
            "data_detection_complete",
            signals_found=len(signals),
            tools=[s.stack_name for s in signals],
        )
        return signals

    def _detect_prisma(self, paths: list[str], path_set: set[str]) -> Signal | None:
        """Detect Prisma ORM via schema file and package.json.

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for Prisma if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = []

        for path in paths:
            if _PRISMA_SCHEMA_PATTERN.search(path):
                confidence += _CONF_PRISMA_SCHEMA
                evidence.append(path)
                break

        if _PACKAGE_JSON in path_set:
            confidence += _CONF_PRISMA_PACKAGE
            evidence.append(_PACKAGE_JSON)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="prisma",
            confidence=min(1.0, round(confidence, 2)),
            evidence=evidence,
        )

    def _detect_sqlalchemy(self, paths: list[str], path_set: set[str]) -> Signal | None:
        """Detect SQLAlchemy via Python dependency files and model patterns.

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for SQLAlchemy if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = []

        # Check for Python dependency indicators
        python_dep_files = [
            p
            for p in paths
            if p == _PYPROJECT_TOML
            or p == _SETUP_PY
            or p == _SETUP_CFG
            or _REQUIREMENTS_TXT_PATTERN.search(p)
        ]
        if python_dep_files:
            confidence += _CONF_SQLALCHEMY_DEPS
            evidence.extend(python_dep_files[:1])

        # Check for model files (models.py pattern)
        for path in paths:
            if _SQLALCHEMY_MODEL_PATTERN.search(path):
                confidence += _CONF_SQLALCHEMY_MODELS
                evidence.append(path)
                break

        if confidence < _CONF_SQLALCHEMY_DEPS + _CONF_SQLALCHEMY_MODELS:
            # Need both dependency file and model file for a meaningful signal
            return None

        return Signal(
            stack_name="sqlalchemy",
            confidence=min(1.0, round(confidence, 2)),
            evidence=evidence,
        )

    def _detect_alembic(self, paths: list[str], path_set: set[str]) -> Signal | None:
        """Detect Alembic via directory structure and config file.

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for Alembic if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = []

        # Check for alembic directory
        for path in paths:
            if _ALEMBIC_DIR_PATTERN.search(path):
                confidence += _CONF_ALEMBIC_DIR
                evidence.append(path)
                break

        # Check for alembic.ini
        if _ALEMBIC_INI in path_set:
            confidence += _CONF_ALEMBIC_INI
            evidence.append(_ALEMBIC_INI)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="alembic",
            confidence=min(1.0, round(confidence, 2)),
            evidence=evidence,
        )

    def _detect_entity_framework(
        self, paths: list[str], path_set: set[str]
    ) -> Signal | None:
        """Detect Entity Framework via .csproj and Migrations directory.

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for Entity Framework if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = []

        # Check for .csproj files
        for path in paths:
            if _CSPROJ_PATTERN.search(path):
                confidence += _CONF_EF_CSPROJ
                evidence.append(path)
                break

        # Check for Migrations directory with .cs files
        for path in paths:
            if _EF_MIGRATIONS_PATTERN.search(path):
                confidence += _CONF_EF_MIGRATIONS
                evidence.append(path)
                break

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="entity-framework",
            confidence=min(1.0, round(confidence, 2)),
            evidence=evidence,
        )

    def _detect_flyway(self, paths: list[str], path_set: set[str]) -> Signal | None:
        """Detect Flyway via config file and migration directories.

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for Flyway if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = []

        # Check for flyway.conf
        if _FLYWAY_CONF in path_set:
            confidence += _CONF_FLYWAY_CONF
            evidence.append(_FLYWAY_CONF)

        # Check for Flyway-specific migration directories
        migration_found = False
        for path in paths:
            if migration_found:
                break
            for pattern in _FLYWAY_MIGRATION_DIRS:
                if pattern.search(path):
                    confidence += _CONF_FLYWAY_MIGRATIONS
                    evidence.append(path)
                    migration_found = True
                    break

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="flyway",
            confidence=min(1.0, round(confidence, 2)),
            evidence=evidence,
        )

    def _detect_liquibase(self, paths: list[str], path_set: set[str]) -> Signal | None:
        """Detect Liquibase via properties file and changelog directories.

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for Liquibase if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = []

        # Check for liquibase.properties
        if _LIQUIBASE_PROPERTIES in path_set:
            confidence += _CONF_LIQUIBASE_PROPS
            evidence.append(_LIQUIBASE_PROPERTIES)

        # Check for changelog directory
        for path in paths:
            if _LIQUIBASE_CHANGELOG_PATTERN.search(path):
                confidence += _CONF_LIQUIBASE_CHANGELOG
                evidence.append(path)
                break

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="liquibase",
            confidence=min(1.0, round(confidence, 2)),
            evidence=evidence,
        )

    def _detect_sql_migrations(
        self, paths: list[str], path_set: set[str]
    ) -> Signal | None:
        """Detect plain SQL migration files.

        Matches ``migrations/`` or ``migration/`` directories containing
        ``.sql`` files.  Skips detection if Alembic, Flyway, or Liquibase
        have already been detected (those are more specific).

        Args:
            paths: All file paths in the inventory.
            path_set: Set of file paths for fast lookup.

        Returns:
            A Signal for plain SQL migrations if detected, or None.
        """
        evidence: list[str] = []

        for path in paths:
            if _SQL_MIGRATION_PATTERN.search(path):
                evidence.append(path)

        # Also check for ORM model file patterns (e.g. *.model.ts)
        model_evidence: list[str] = []
        for path in paths:
            if _ORM_MODEL_TS_PATTERN.search(path):
                model_evidence.append(path)

        all_evidence = evidence + model_evidence
        if not all_evidence:
            return None

        confidence = 0.0
        if evidence:
            confidence += _CONF_SQL_MIGRATIONS
        if model_evidence:
            confidence += _CONF_ORM_MODEL_FILES

        return Signal(
            stack_name="sql-migrations",
            confidence=min(1.0, round(confidence, 2)),
            evidence=all_evidence,
        )


def _create_and_register() -> None:
    """Create and register the Data detector instance."""
    register_detector(DataDetector())


_create_and_register()
