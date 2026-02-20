"""Unit tests for the middleware analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.middleware import analyze_middleware
from repo_mirror_kit.harvester.analyzers.surfaces import MiddlewareSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(files: list[FileEntry]) -> InventoryResult:
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=sum(f.size for f in files),
        total_skipped=0,
    )


def _make_profile() -> StackProfile:
    return StackProfile(stacks={}, evidence={}, signals=[])


def _write_file(tmp_path: Path, rel_path: str, content: str) -> FileEntry:
    full_path = tmp_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    ext = ""
    dot = rel_path.rfind(".")
    if dot != -1:
        ext = rel_path[dot:]
    return FileEntry(
        path=rel_path, size=len(content), extension=ext, hash="abc123", category="source"
    )


# ---------------------------------------------------------------------------
# Empty / no matches
# ---------------------------------------------------------------------------


class TestEmptyResults:
    """Verify analyzer returns empty list when no middleware patterns are present."""

    def test_no_middleware_patterns(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/utils.ts",
            "export function add(a: number, b: number) { return a + b; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert result == []

    def test_no_workdir_returns_empty(self) -> None:
        entry = FileEntry(
            path="src/app.ts", size=100, extension=".ts", hash="abc123", category="source"
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=None)

        assert result == []

    def test_non_source_files_skipped(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "config/nginx.conf",
            "server { listen 80; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert result == []


# ---------------------------------------------------------------------------
# Express / Koa patterns
# ---------------------------------------------------------------------------


class TestExpressDetection:
    """Tests for Express app.use() middleware detection."""

    def test_app_use_with_named_middleware(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.ts",
            """\
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';

const app = express();
app.use(cors);
app.use(helmet);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 2
        express_surfaces = [s for s in result if s.middleware_type == "express"]
        assert len(express_surfaces) == 2
        names = {s.name for s in express_surfaces}
        assert "express:cors" in names
        assert "express:helmet" in names

    def test_app_use_with_route_path(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.ts",
            """\
const app = express();
app.use('/api', authMiddleware);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 1
        surface = result[0]
        assert surface.middleware_type == "express"
        assert "/api" in surface.applies_to

    def test_express_middleware_has_execution_order(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/server.ts",
            """\
const app = express();
app.use(first);
app.use(second);
app.use(third);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        express_surfaces = [s for s in result if s.middleware_type == "express"]
        assert len(express_surfaces) == 3
        orders = [s.execution_order for s in express_surfaces]
        assert orders == [1, 2, 3]

    def test_router_use_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/routes/api.ts",
            """\
const router = express.Router();
router.use(validateToken);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 1
        assert result[0].middleware_type == "express"

    def test_express_applies_to_wildcard_when_no_path(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.ts",
            "app.use(logger);\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 1
        assert result[0].applies_to == ["*"]

    def test_surface_type_is_middleware(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.ts",
            "app.use(cors);\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert isinstance(surface, MiddlewareSurface)
            assert surface.surface_type == "middleware"


# ---------------------------------------------------------------------------
# Django patterns
# ---------------------------------------------------------------------------


class TestDjangoDetection:
    """Tests for Django MIDDLEWARE list detection."""

    def test_middleware_list_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "myproject/settings.py",
            """\
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
]
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 3
        for surface in result:
            assert surface.middleware_type == "django"

        names = [s.name for s in result]
        assert "django:SecurityMiddleware" in names
        assert "django:SessionMiddleware" in names
        assert "django:CommonMiddleware" in names

    def test_django_middleware_has_execution_order(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "config/settings.py",
            """\
MIDDLEWARE = [
    'first.Middleware',
    'second.Middleware',
]
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 2
        assert result[0].execution_order == 1
        assert result[1].execution_order == 2

    def test_django_applies_to_wildcard(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "settings.py",
            "MIDDLEWARE = ['django.middleware.common.CommonMiddleware']\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert result[0].applies_to == ["*"]

    def test_django_transforms_has_full_dotpath(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "settings.py",
            "MIDDLEWARE = ['django.contrib.sessions.middleware.SessionMiddleware']\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert "django.contrib.sessions.middleware.SessionMiddleware" in result[0].transforms


# ---------------------------------------------------------------------------
# FastAPI patterns
# ---------------------------------------------------------------------------


class TestFastAPIDetection:
    """Tests for FastAPI Depends(), add_middleware(), and @app.middleware patterns."""

    def test_depends_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/main.py",
            """\
from fastapi import Depends, FastAPI

def get_db():
    pass

@app.get("/items")
def read_items(db = Depends(get_db)):
    return []
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        depends_surfaces = [s for s in result if s.middleware_type == "fastapi_depends"]
        assert len(depends_surfaces) >= 1
        assert depends_surfaces[0].name == "fastapi:depends:get_db"
        assert depends_surfaces[0].transforms == ["get_db"]

    def test_add_middleware_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/main.py",
            """\
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(CORSMiddleware, allow_origins=["*"])
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        class_surfaces = [s for s in result if s.middleware_type == "fastapi_class"]
        assert len(class_surfaces) == 1
        assert class_surfaces[0].name == "fastapi:CORSMiddleware"
        assert class_surfaces[0].transforms == ["CORSMiddleware"]

    def test_middleware_decorator_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/main.py",
            """\
from fastapi import FastAPI

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request, call_next):
    response = await call_next(request)
    return response
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        decorator_surfaces = [s for s in result if s.middleware_type == "fastapi_decorator"]
        assert len(decorator_surfaces) == 1
        assert decorator_surfaces[0].transforms == ["http"]

    def test_fastapi_applies_to_wildcard(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.py",
            "app.add_middleware(GZipMiddleware)\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert surface.applies_to == ["*"]


# ---------------------------------------------------------------------------
# Flask patterns
# ---------------------------------------------------------------------------


class TestFlaskDetection:
    """Tests for Flask request hook detection."""

    def test_before_request_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.py",
            """\
from flask import Flask

app = Flask(__name__)

@app.before_request
def check_auth():
    pass
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        flask_surfaces = [s for s in result if s.middleware_type == "flask_hook"]
        assert len(flask_surfaces) == 1
        assert flask_surfaces[0].transforms == ["before_request"]

    def test_after_request_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.py",
            """\
@app.after_request
def add_headers(response):
    return response
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        flask_surfaces = [s for s in result if s.middleware_type == "flask_hook"]
        assert len(flask_surfaces) == 1
        assert flask_surfaces[0].transforms == ["after_request"]


# ---------------------------------------------------------------------------
# ASP.NET patterns
# ---------------------------------------------------------------------------


class TestAspNetDetection:
    """Tests for ASP.NET Use* pipeline middleware detection."""

    def test_use_pipeline_methods_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/Program.ts",
            """\
const app = builder.build();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        aspnet_surfaces = [s for s in result if s.middleware_type == "aspnet"]
        assert len(aspnet_surfaces) == 3
        names = {s.name for s in aspnet_surfaces}
        assert "aspnet:UseRouting" in names
        assert "aspnet:UseAuthentication" in names
        assert "aspnet:UseAuthorization" in names

    def test_aspnet_has_execution_order(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/Startup.ts",
            """\
app.UseRouting();
app.UseAuthentication();
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        aspnet_surfaces = [s for s in result if s.middleware_type == "aspnet"]
        assert len(aspnet_surfaces) == 2
        assert aspnet_surfaces[0].execution_order == 1
        assert aspnet_surfaces[1].execution_order == 2


# ---------------------------------------------------------------------------
# Source refs and surface type
# ---------------------------------------------------------------------------


class TestSourceRefsAndSurfaceType:
    """Verify source_refs are populated and surface_type is correct."""

    def test_source_refs_populated_for_express(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/app.ts",
            "app.use(cors);\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) >= 1
        for surface in result:
            assert len(surface.source_refs) == 1
            assert surface.source_refs[0].file_path == "src/app.ts"
            assert surface.source_refs[0].start_line is not None
            assert surface.source_refs[0].start_line > 0

    def test_all_surfaces_are_middleware_type(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "settings.py",
            "MIDDLEWARE = ['django.middleware.common.CommonMiddleware']\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert isinstance(surface, MiddlewareSurface)
            assert surface.surface_type == "middleware"


# ---------------------------------------------------------------------------
# Multiple frameworks
# ---------------------------------------------------------------------------


class TestMultipleFrameworks:
    """Tests for repositories using multiple framework middleware patterns."""

    def test_django_and_fastapi_in_same_repo(self, tmp_path: Path) -> None:
        entry1 = _write_file(
            tmp_path,
            "myproject/settings.py",
            "MIDDLEWARE = ['django.middleware.common.CommonMiddleware']\n",
        )
        entry2 = _write_file(
            tmp_path,
            "api/main.py",
            "app.add_middleware(CORSMiddleware)\n",
        )
        inventory = _make_inventory([entry1, entry2])
        result = analyze_middleware(inventory, _make_profile(), workdir=tmp_path)

        types = {s.middleware_type for s in result}
        assert "django" in types
        assert "fastapi_class" in types
