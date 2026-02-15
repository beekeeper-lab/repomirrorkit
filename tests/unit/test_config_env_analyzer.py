"""Unit tests for the config & environment variable analyzer."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.config_env import analyze_config
from repo_mirror_kit.harvester.analyzers.surfaces import ConfigSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
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
            extension="." + p.rsplit(".", 1)[-1] if "." in p else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=len(files) * 100,
        total_skipped=0,
    )


def _make_profile(stacks: dict[str, float]) -> StackProfile:
    """Build a StackProfile with the given stacks."""
    return StackProfile(
        stacks=stacks,
        evidence={name: [] for name in stacks},
        signals=[],
    )


def _write_file(workdir: Path, rel_path: str, content: str) -> None:
    """Write a file under workdir with the given content."""
    full = workdir / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(textwrap.dedent(content), encoding="utf-8")


def _find_surface(
    surfaces: list[ConfigSurface], env_var_name: str
) -> ConfigSurface | None:
    """Find a surface by env_var_name."""
    for s in surfaces:
        if s.env_var_name == env_var_name:
            return s
    return None


# ---------------------------------------------------------------------------
# No-op when no frameworks detected and no config files
# ---------------------------------------------------------------------------


class TestNoFrameworkDetected:
    """Analyzer returns empty when nothing is detected."""

    def test_empty_profile_empty_inventory(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        profile = _make_profile({})
        result = analyze_config(inventory, profile, tmp_path)
        assert result == []

    def test_unrelated_stack_no_config_files(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "src/app.rb", "puts 'hello'")
        inventory = _make_inventory(["src/app.rb"])
        profile = _make_profile({"rails": 0.9})
        result = analyze_config(inventory, profile, tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# Node.js / TypeScript config patterns
# ---------------------------------------------------------------------------


class TestJSConfigExtraction:
    """Extract process.env references from JS/TS files."""

    def test_process_env_dot_simple(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.js",
            """\
            const port = process.env.PORT;
            const host = process.env.HOST;
            """,
        )
        inventory = _make_inventory(["src/config.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        assert len(surfaces) >= 2
        port = _find_surface(surfaces, "PORT")
        assert port is not None
        assert port.required is True
        assert port.default_value is None

        host = _find_surface(surfaces, "HOST")
        assert host is not None

    def test_process_env_bracket(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.ts",
            """\
            const secret = process.env["JWT_SECRET"];
            """,
        )
        inventory = _make_inventory(["src/config.ts"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        jwt = _find_surface(surfaces, "JWT_SECRET")
        assert jwt is not None
        assert jwt.required is True

    def test_process_env_with_default(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/server.js",
            """\
            const port = process.env.PORT || '3000';
            const host = process.env.HOST ?? 'localhost';
            """,
        )
        inventory = _make_inventory(["src/server.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        port = _find_surface(surfaces, "PORT")
        assert port is not None
        assert port.default_value == "3000"
        assert port.required is False

        host = _find_surface(surfaces, "HOST")
        assert host is not None
        assert host.default_value == "localhost"
        assert host.required is False

    def test_process_env_bracket_with_default(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/app.ts",
            """\
            const mode = process.env["NODE_ENV"] || 'development';
            """,
        )
        inventory = _make_inventory(["src/app.ts"])
        profile = _make_profile({"nextjs": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        mode = _find_surface(surfaces, "NODE_ENV")
        assert mode is not None
        assert mode.default_value == "development"
        assert mode.required is False

    def test_tsx_file_detected(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/App.tsx",
            """\
            const apiUrl = process.env.API_URL;
            """,
        )
        inventory = _make_inventory(["src/App.tsx"])
        profile = _make_profile({"react": 0.9})
        surfaces = analyze_config(inventory, profile, tmp_path)

        api = _find_surface(surfaces, "API_URL")
        assert api is not None

    def test_multiple_files_same_var(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/server.js",
            "const port = process.env.PORT || '3000';",
        )
        _write_file(
            tmp_path,
            "src/config.js",
            "const p = process.env.PORT;",
        )
        inventory = _make_inventory(["src/server.js", "src/config.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        port = _find_surface(surfaces, "PORT")
        assert port is not None
        # Should be consolidated: has default from server.js
        assert port.default_value == "3000"
        assert port.required is False
        assert len(port.usage_locations) == 2


# ---------------------------------------------------------------------------
# Python config patterns
# ---------------------------------------------------------------------------


class TestPythonConfigExtraction:
    """Extract os.environ/os.getenv references from Python files."""

    def test_os_environ_bracket(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.py",
            """\
            import os
            db_url = os.environ["DATABASE_URL"]
            """,
        )
        inventory = _make_inventory(["src/config.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        db = _find_surface(surfaces, "DATABASE_URL")
        assert db is not None
        assert db.required is True
        assert db.default_value is None

    def test_os_getenv_no_default(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/settings.py",
            """\
            import os
            secret = os.getenv("SECRET_KEY")
            """,
        )
        inventory = _make_inventory(["src/settings.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        secret = _find_surface(surfaces, "SECRET_KEY")
        assert secret is not None
        assert secret.required is True

    def test_os_getenv_with_default(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/settings.py",
            """\
            import os
            debug = os.getenv("DEBUG", "false")
            """,
        )
        inventory = _make_inventory(["src/settings.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        debug = _find_surface(surfaces, "DEBUG")
        assert debug is not None
        assert debug.default_value == "false"
        assert debug.required is False

    def test_os_environ_get(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/app.py",
            """\
            import os
            log_level = os.environ.get("LOG_LEVEL", "INFO")
            """,
        )
        inventory = _make_inventory(["src/app.py"])
        profile = _make_profile({"flask": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        log = _find_surface(surfaces, "LOG_LEVEL")
        assert log is not None
        assert log.default_value == "INFO"
        assert log.required is False

    def test_multiple_python_patterns(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.py",
            """\
            import os
            db = os.environ["DATABASE_URL"]
            secret = os.getenv("SECRET_KEY", "dev-secret")
            debug = os.environ.get("DEBUG", "true")
            """,
        )
        inventory = _make_inventory(["src/config.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        assert len(surfaces) >= 3
        db = _find_surface(surfaces, "DATABASE_URL")
        assert db is not None
        assert db.required is True

        secret = _find_surface(surfaces, "SECRET_KEY")
        assert secret is not None
        assert secret.required is False

        debug = _find_surface(surfaces, "DEBUG")
        assert debug is not None
        assert debug.default_value == "true"


# ---------------------------------------------------------------------------
# .NET config patterns
# ---------------------------------------------------------------------------


class TestDotnetConfigExtraction:
    """Extract .NET environment and configuration references."""

    def test_get_environment_variable(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Program.cs",
            """\
            var conn = Environment.GetEnvironmentVariable("CONNECTION_STRING");
            """,
        )
        inventory = _make_inventory(["Program.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        conn = _find_surface(surfaces, "CONNECTION_STRING")
        assert conn is not None
        assert conn.required is True

    def test_iconfiguration_bracket(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Startup.cs",
            """\
            var val = IConfiguration["Logging:LogLevel:Default"];
            """,
        )
        inventory = _make_inventory(["Startup.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        val = _find_surface(surfaces, "Logging:LogLevel:Default")
        assert val is not None

    def test_config_bracket(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "Controllers/HomeController.cs",
            """\
            var apiKey = _configuration["ApiKeys:Google"];
            """,
        )
        inventory = _make_inventory(["Controllers/HomeController.cs"])
        profile = _make_profile({"aspnet": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        key = _find_surface(surfaces, "ApiKeys:Google")
        assert key is not None


# ---------------------------------------------------------------------------
# Dotenv file extraction
# ---------------------------------------------------------------------------


class TestDotenvExtraction:
    """Extract env vars from .env files."""

    def test_basic_dotenv(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            """\
            PORT=3000
            HOST=localhost
            """,
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        port = _find_surface(surfaces, "PORT")
        assert port is not None
        assert port.default_value == "3000"
        assert port.required is False

        host = _find_surface(surfaces, "HOST")
        assert host is not None
        assert host.default_value == "localhost"

    def test_dotenv_with_quotes(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            """\
            DB_URL="postgres://localhost/db"
            SECRET='my-secret'
            """,
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        db = _find_surface(surfaces, "DB_URL")
        assert db is not None
        assert db.default_value == "postgres://localhost/db"

        secret = _find_surface(surfaces, "SECRET")
        assert secret is not None
        assert secret.default_value == "my-secret"

    def test_dotenv_comments_skipped(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            """\
            # This is a comment
            PORT=3000
            # Another comment
            """,
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].env_var_name == "PORT"

    def test_dotenv_example_no_defaults(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env.example",
            """\
            DATABASE_URL=
            SECRET_KEY=change-me
            """,
        )
        inventory = _make_inventory([".env.example"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        db = _find_surface(surfaces, "DATABASE_URL")
        assert db is not None
        # Example files don't provide real defaults
        assert db.default_value is None
        assert db.required is True

        secret = _find_surface(surfaces, "SECRET_KEY")
        assert secret is not None
        assert secret.default_value is None
        assert secret.required is True

    def test_dotenv_local(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env.local",
            """\
            API_KEY=local-key-123
            """,
        )
        inventory = _make_inventory([".env.local"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        api = _find_surface(surfaces, "API_KEY")
        assert api is not None
        assert api.default_value == "local-key-123"

    def test_dotenv_empty_value(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            """\
            EMPTY_VAR=
            """,
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        empty = _find_surface(surfaces, "EMPTY_VAR")
        assert empty is not None
        # Empty value in .env means no meaningful default
        assert empty.default_value is None


# ---------------------------------------------------------------------------
# appsettings.json extraction
# ---------------------------------------------------------------------------


class TestAppsettingsExtraction:
    """Extract config keys from appsettings.json."""

    def test_flat_keys(self, tmp_path: Path) -> None:
        data = {"ConnectionString": "server=localhost", "LogLevel": "Warning"}
        _write_file(tmp_path, "appsettings.json", json.dumps(data))
        inventory = _make_inventory(["appsettings.json"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        conn = _find_surface(surfaces, "ConnectionString")
        assert conn is not None
        assert conn.default_value == "server=localhost"
        assert conn.required is False

    def test_nested_keys(self, tmp_path: Path) -> None:
        data = {"Logging": {"LogLevel": {"Default": "Information"}}}
        _write_file(tmp_path, "appsettings.json", json.dumps(data))
        inventory = _make_inventory(["appsettings.json"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        log = _find_surface(surfaces, "Logging:LogLevel:Default")
        assert log is not None
        assert log.default_value == "Information"

    def test_appsettings_environment_variant(self, tmp_path: Path) -> None:
        data = {"ApiKey": "test-key"}
        _write_file(tmp_path, "appsettings.Development.json", json.dumps(data))
        inventory = _make_inventory(["appsettings.Development.json"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        key = _find_surface(surfaces, "ApiKey")
        assert key is not None

    def test_invalid_json_skipped(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "appsettings.json", "not valid json {{{")
        inventory = _make_inventory(["appsettings.json"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)
        assert surfaces == []


# ---------------------------------------------------------------------------
# Docker Compose environment extraction
# ---------------------------------------------------------------------------


class TestDockerComposeExtraction:
    """Extract env vars from docker-compose.yml."""

    def test_docker_compose_environment(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "docker-compose.yml",
            """\
            services:
              app:
                image: myapp
                environment:
                  - NODE_ENV=production
                  - PORT=8080
                  - SECRET_KEY
            """,
        )
        inventory = _make_inventory(["docker-compose.yml"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        node_env = _find_surface(surfaces, "NODE_ENV")
        assert node_env is not None
        assert node_env.default_value == "production"

        port = _find_surface(surfaces, "PORT")
        assert port is not None
        assert port.default_value == "8080"

        secret = _find_surface(surfaces, "SECRET_KEY")
        assert secret is not None
        assert secret.default_value is None
        assert secret.required is True


# ---------------------------------------------------------------------------
# Feature flag detection
# ---------------------------------------------------------------------------


class TestFeatureFlagDetection:
    """Identify feature flags by naming convention."""

    def test_feature_prefix(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            """\
            FEATURE_DARK_MODE=true
            FF_NEW_CHECKOUT=1
            ENABLE_BETA=false
            """,
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        dark = _find_surface(surfaces, "FEATURE_DARK_MODE")
        assert dark is not None
        assert dark.name.startswith("flag:")

        ff = _find_surface(surfaces, "FF_NEW_CHECKOUT")
        assert ff is not None
        assert ff.name.startswith("flag:")

        enable = _find_surface(surfaces, "ENABLE_BETA")
        assert enable is not None
        assert enable.name.startswith("flag:")

    def test_enabled_suffix(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.js",
            "const v = process.env.DARK_MODE_ENABLED;",
        )
        inventory = _make_inventory(["src/config.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        dark = _find_surface(surfaces, "DARK_MODE_ENABLED")
        assert dark is not None
        assert dark.name.startswith("flag:")


# ---------------------------------------------------------------------------
# External service detection
# ---------------------------------------------------------------------------


class TestExternalServiceDetection:
    """Identify external service dependencies."""

    def test_database_url(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.py",
            """\
            import os
            db = os.environ["DATABASE_URL"]
            """,
        )
        inventory = _make_inventory(["src/config.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        db = _find_surface(surfaces, "DATABASE_URL")
        assert db is not None
        assert db.name.startswith("service:")

    def test_redis_url(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            "REDIS_URL=redis://localhost:6379",
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        redis = _find_surface(surfaces, "REDIS_URL")
        assert redis is not None
        assert redis.name.startswith("service:")

    def test_api_key_pattern(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            ".env",
            "STRIPE_API_KEY=sk_test_123",
        )
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        stripe = _find_surface(surfaces, "STRIPE_API_KEY")
        assert stripe is not None
        assert stripe.name.startswith("service:")


# ---------------------------------------------------------------------------
# Deduplication / consolidation
# ---------------------------------------------------------------------------


class TestConsolidation:
    """Verify that duplicate vars across sources are consolidated."""

    def test_same_var_in_dotenv_and_source(self, tmp_path: Path) -> None:
        _write_file(tmp_path, ".env", "PORT=3000")
        _write_file(
            tmp_path,
            "src/server.js",
            "const port = process.env.PORT;",
        )
        inventory = _make_inventory([".env", "src/server.js"])
        profile = _make_profile({"express": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        port = _find_surface(surfaces, "PORT")
        assert port is not None
        # Should have merged: default from .env, reference from both files
        assert port.default_value == "3000"
        assert port.required is False
        assert len(port.usage_locations) == 2

    def test_no_duplicate_surfaces(self, tmp_path: Path) -> None:
        _write_file(tmp_path, ".env", "PORT=3000")
        _write_file(tmp_path, ".env.local", "PORT=4000")
        inventory = _make_inventory([".env", ".env.local"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        port_surfaces = [s for s in surfaces if s.env_var_name == "PORT"]
        assert len(port_surfaces) == 1


# ---------------------------------------------------------------------------
# Cross-ecosystem detection
# ---------------------------------------------------------------------------


class TestCrossEcosystem:
    """Analyzer runs across all detected ecosystems."""

    def test_mixed_stacks(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/app.py",
            """\
            import os
            db = os.environ["DATABASE_URL"]
            """,
        )
        _write_file(
            tmp_path,
            "frontend/config.ts",
            "const api = process.env.API_URL;",
        )
        _write_file(tmp_path, ".env", "LOG_LEVEL=debug")
        inventory = _make_inventory(["src/app.py", "frontend/config.ts", ".env"])
        profile = _make_profile({"fastapi": 0.8, "react": 0.9})
        surfaces = analyze_config(inventory, profile, tmp_path)

        assert _find_surface(surfaces, "DATABASE_URL") is not None
        assert _find_surface(surfaces, "API_URL") is not None
        assert _find_surface(surfaces, "LOG_LEVEL") is not None


# ---------------------------------------------------------------------------
# Surface structure validation
# ---------------------------------------------------------------------------


class TestSurfaceStructure:
    """Each ConfigSurface has correct type and fields."""

    def test_surface_type_is_config(self, tmp_path: Path) -> None:
        _write_file(tmp_path, ".env", "MY_VAR=hello")
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        assert len(surfaces) == 1
        assert surfaces[0].surface_type == "config"

    def test_source_refs_populated(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/config.py",
            """\
            import os
            val = os.getenv("MY_VAR", "default")
            """,
        )
        inventory = _make_inventory(["src/config.py"])
        profile = _make_profile({"fastapi": 0.8})
        surfaces = analyze_config(inventory, profile, tmp_path)

        var = _find_surface(surfaces, "MY_VAR")
        assert var is not None
        assert len(var.source_refs) >= 1
        assert var.source_refs[0].file_path == "src/config.py"
        assert var.source_refs[0].start_line is not None

    def test_to_dict_serialization(self, tmp_path: Path) -> None:
        _write_file(tmp_path, ".env", "PORT=3000")
        inventory = _make_inventory([".env"])
        profile = _make_profile({})
        surfaces = analyze_config(inventory, profile, tmp_path)

        d = surfaces[0].to_dict()
        assert "env_var_name" in d
        assert "default_value" in d
        assert "required" in d
        assert "usage_locations" in d
        assert "surface_type" in d
        assert d["surface_type"] == "config"
