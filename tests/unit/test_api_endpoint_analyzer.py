"""Unit tests for the API endpoint analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.apis import analyze_api_endpoints
from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface
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
        evidence={},
        signals=[],
    )


def _setup_files(tmp_path: Path, file_contents: dict[str, str]) -> None:
    """Create files in tmp_path with given content."""
    for rel_path, content in file_contents.items():
        full_path = tmp_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")


def _find_surface(
    surfaces: list[ApiSurface], method: str, path: str
) -> ApiSurface | None:
    """Find a surface by method and path."""
    for s in surfaces:
        if s.method == method and s.path == path:
            return s
    return None


# ---------------------------------------------------------------------------
# No-op when framework not detected
# ---------------------------------------------------------------------------


class TestNoDetectedFrameworks:
    """Analyzer produces nothing when no relevant stacks are detected."""

    def test_empty_profile(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        profile = _make_profile({})
        result = analyze_api_endpoints(tmp_path, inventory, profile)
        assert result == []

    def test_unrelated_stack(self, tmp_path: Path) -> None:
        inventory = _make_inventory(["src/app.py"])
        profile = _make_profile({"react": 0.8})
        _setup_files(tmp_path, {"src/app.py": "@app.get('/test')\ndef test(): ..."})
        result = analyze_api_endpoints(tmp_path, inventory, profile)
        assert result == []


# ---------------------------------------------------------------------------
# Express endpoint extraction
# ---------------------------------------------------------------------------


class TestExpressExtraction:
    """Extract endpoints from Express route definitions."""

    def test_basic_get(self, tmp_path: Path) -> None:
        code = "app.get('/users', getUsers);"
        _setup_files(tmp_path, {"src/routes.js": code})
        inventory = _make_inventory(["src/routes.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "GET"
        assert surfaces[0].path == "/users"

    def test_multiple_methods(self, tmp_path: Path) -> None:
        code = (
            "app.get('/items', listItems);\n"
            "app.post('/items', createItem);\n"
            "app.delete('/items/:id', deleteItem);\n"
        )
        _setup_files(tmp_path, {"routes/items.js": code})
        inventory = _make_inventory(["routes/items.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 3
        methods = {s.method for s in surfaces}
        assert methods == {"GET", "POST", "DELETE"}

    def test_router_pattern(self, tmp_path: Path) -> None:
        code = "router.post('/auth/login', handleLogin);"
        _setup_files(tmp_path, {"routes/auth.ts": code})
        inventory = _make_inventory(["routes/auth.ts"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "POST"
        assert surfaces[0].path == "/auth/login"

    def test_auth_hint_detected(self, tmp_path: Path) -> None:
        code = (
            "const authenticate = require('./auth');\n"
            "app.get('/protected', authenticate, handler);\n"
        )
        _setup_files(tmp_path, {"src/api.js": code})
        inventory = _make_inventory(["src/api.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == "required"

    def test_no_auth_when_absent(self, tmp_path: Path) -> None:
        code = "app.get('/public', handler);"
        _setup_files(tmp_path, {"src/api.js": code})
        inventory = _make_inventory(["src/api.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == ""

    def test_source_ref_populated(self, tmp_path: Path) -> None:
        code = "// comment\napp.get('/test', handler);"
        _setup_files(tmp_path, {"src/routes.js": code})
        inventory = _make_inventory(["src/routes.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].source_refs[0].file_path == "src/routes.js"
        assert surfaces[0].source_refs[0].start_line == 2

    def test_surface_type_is_api(self, tmp_path: Path) -> None:
        code = "app.get('/test', handler);"
        _setup_files(tmp_path, {"src/routes.js": code})
        inventory = _make_inventory(["src/routes.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].surface_type == "api"

    def test_skips_non_js_files(self, tmp_path: Path) -> None:
        code = "app.get('/test', handler);"
        _setup_files(tmp_path, {"src/readme.md": code})
        inventory = _make_inventory(["src/readme.md"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []

    def test_double_quoted_path(self, tmp_path: Path) -> None:
        code = 'app.get("/users", handler);'
        _setup_files(tmp_path, {"src/app.js": code})
        inventory = _make_inventory(["src/app.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/users"


# ---------------------------------------------------------------------------
# Fastify endpoint extraction
# ---------------------------------------------------------------------------


class TestFastifyExtraction:
    """Extract endpoints from Fastify route definitions."""

    def test_fastify_route(self, tmp_path: Path) -> None:
        code = "fastify.get('/health', healthHandler);"
        _setup_files(tmp_path, {"src/server.js": code})
        inventory = _make_inventory(["src/server.js"])
        profile = _make_profile({"fastify": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "GET"
        assert surfaces[0].path == "/health"

    def test_no_duplicates_when_express_also_detected(self, tmp_path: Path) -> None:
        code = "app.get('/shared', handler);"
        _setup_files(tmp_path, {"src/app.js": code})
        inventory = _make_inventory(["src/app.js"])
        profile = _make_profile({"express": 0.7, "fastify": 0.5})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        # Should not duplicate since Express was also detected
        assert len(surfaces) == 1


# ---------------------------------------------------------------------------
# NestJS endpoint extraction
# ---------------------------------------------------------------------------


class TestNestJSExtraction:
    """Extract endpoints from NestJS controller decorators."""

    def test_basic_controller(self, tmp_path: Path) -> None:
        code = (
            "import { Controller, Get, Post } from '@nestjs/common';\n\n"
            "@Controller('users')\n"
            "export class UsersController {\n"
            "  @Get()\n"
            "  findAll() {}\n\n"
            "  @Post()\n"
            "  create() {}\n"
            "}\n"
        )
        _setup_files(tmp_path, {"src/users/users.controller.ts": code})
        inventory = _make_inventory(["src/users/users.controller.ts"])
        profile = _make_profile({"nestjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 2
        get_surface = _find_surface(surfaces, "GET", "/users")
        assert get_surface is not None
        post_surface = _find_surface(surfaces, "POST", "/users")
        assert post_surface is not None

    def test_controller_with_sub_paths(self, tmp_path: Path) -> None:
        code = (
            "@Controller('items')\n"
            "export class ItemsController {\n"
            "  @Get(':id')\n"
            "  findOne() {}\n"
            "}\n"
        )
        _setup_files(tmp_path, {"src/items.controller.ts": code})
        inventory = _make_inventory(["src/items.controller.ts"])
        profile = _make_profile({"nestjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/items/:id"

    def test_nestjs_auth_guard(self, tmp_path: Path) -> None:
        code = (
            "@Controller('admin')\n"
            "@UseGuards(JwtAuthGuard)\n"
            "export class AdminController {\n"
            "  @Get()\n"
            "  dashboard() {}\n"
            "}\n"
        )
        _setup_files(tmp_path, {"src/admin.controller.ts": code})
        inventory = _make_inventory(["src/admin.controller.ts"])
        profile = _make_profile({"nestjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == "required"

    def test_controller_without_prefix(self, tmp_path: Path) -> None:
        code = (
            "@Controller()\n"
            "export class RootController {\n"
            "  @Get('health')\n"
            "  health() {}\n"
            "}\n"
        )
        _setup_files(tmp_path, {"src/root.controller.ts": code})
        inventory = _make_inventory(["src/root.controller.ts"])
        profile = _make_profile({"nestjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/health"

    def test_skips_non_controller_files(self, tmp_path: Path) -> None:
        code = "@Get('test')\nfindAll() {}"
        _setup_files(tmp_path, {"src/app.service.ts": code})
        inventory = _make_inventory(["src/app.service.ts"])
        profile = _make_profile({"nestjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []


# ---------------------------------------------------------------------------
# FastAPI endpoint extraction
# ---------------------------------------------------------------------------


class TestFastAPIExtraction:
    """Extract endpoints from FastAPI route decorators."""

    def test_basic_routes(self, tmp_path: Path) -> None:
        code = (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n"
            "@app.get('/items')\n"
            "async def list_items():\n"
            "    pass\n\n"
            "@app.post('/items')\n"
            "async def create_item():\n"
            "    pass\n"
        )
        _setup_files(tmp_path, {"src/main.py": code})
        inventory = _make_inventory(["src/main.py"])
        profile = _make_profile({"fastapi": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 2
        get_surface = _find_surface(surfaces, "GET", "/items")
        assert get_surface is not None
        post_surface = _find_surface(surfaces, "POST", "/items")
        assert post_surface is not None

    def test_router_pattern(self, tmp_path: Path) -> None:
        code = (
            "from fastapi import APIRouter\n\n"
            "router = APIRouter()\n\n"
            "@router.get('/users/{user_id}')\n"
            "async def get_user(user_id: int):\n"
            "    pass\n"
        )
        _setup_files(tmp_path, {"src/routers/users.py": code})
        inventory = _make_inventory(["src/routers/users.py"])
        profile = _make_profile({"fastapi": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/users/{user_id}"

    def test_auth_dependency(self, tmp_path: Path) -> None:
        code = (
            "from fastapi import Depends\n\n"
            "@app.get('/secure')\n"
            "async def secure(user=Depends(get_current_user)):\n"
            "    pass\n"
        )
        _setup_files(tmp_path, {"src/api.py": code})
        inventory = _make_inventory(["src/api.py"])
        profile = _make_profile({"fastapi": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == "required"

    def test_response_model_hint(self, tmp_path: Path) -> None:
        code = (
            "@app.get('/items', response_model=ItemList)\n"
            "async def list_items():\n"
            "    pass\n"
        )
        _setup_files(tmp_path, {"src/api.py": code})
        inventory = _make_inventory(["src/api.py"])
        profile = _make_profile({"fastapi": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].response_schema.get("type") == "ItemList"

    def test_skips_non_python_files(self, tmp_path: Path) -> None:
        code = "@app.get('/test')\nasync def test(): pass"
        _setup_files(tmp_path, {"src/app.js": code})
        inventory = _make_inventory(["src/app.js"])
        profile = _make_profile({"fastapi": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []


# ---------------------------------------------------------------------------
# Flask endpoint extraction
# ---------------------------------------------------------------------------


class TestFlaskExtraction:
    """Extract endpoints from Flask route decorators."""

    def test_basic_route(self, tmp_path: Path) -> None:
        code = (
            "from flask import Flask\n\n"
            "app = Flask(__name__)\n\n"
            "@app.route('/hello')\n"
            "def hello():\n"
            "    return 'Hello'\n"
        )
        _setup_files(tmp_path, {"app.py": code})
        inventory = _make_inventory(["app.py"])
        profile = _make_profile({"flask": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "GET"
        assert surfaces[0].path == "/hello"

    def test_route_with_methods(self, tmp_path: Path) -> None:
        code = "@app.route('/data', methods=['GET', 'POST'])\ndef data(): pass"
        _setup_files(tmp_path, {"views.py": code})
        inventory = _make_inventory(["views.py"])
        profile = _make_profile({"flask": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 2
        methods = {s.method for s in surfaces}
        assert methods == {"GET", "POST"}

    def test_blueprint_route(self, tmp_path: Path) -> None:
        code = (
            "from flask import Blueprint\n\n"
            "bp = Blueprint('auth', __name__)\n\n"
            "@bp.route('/login', methods=['POST'])\n"
            "def login():\n"
            "    pass\n"
        )
        _setup_files(tmp_path, {"blueprints/auth.py": code})
        inventory = _make_inventory(["blueprints/auth.py"])
        profile = _make_profile({"flask": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "POST"
        assert surfaces[0].path == "/login"

    def test_flask_auth_decorator(self, tmp_path: Path) -> None:
        code = "@login_required\n@app.route('/profile')\ndef profile():\n    pass\n"
        _setup_files(tmp_path, {"views.py": code})
        inventory = _make_inventory(["views.py"])
        profile = _make_profile({"flask": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == "required"


# ---------------------------------------------------------------------------
# .NET minimal API endpoint extraction
# ---------------------------------------------------------------------------


class TestDotnetMinimalApiExtraction:
    """Extract endpoints from .NET minimal API calls."""

    def test_map_get(self, tmp_path: Path) -> None:
        code = 'app.MapGet("/weatherforecast", () => { });'
        _setup_files(tmp_path, {"Program.cs": code})
        inventory = _make_inventory(["Program.cs"])
        profile = _make_profile({"dotnet-minimal-api": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "GET"
        assert surfaces[0].path == "/weatherforecast"

    def test_multiple_map_methods(self, tmp_path: Path) -> None:
        code = (
            'app.MapGet("/items", () => { });\n'
            'app.MapPost("/items", () => { });\n'
            'app.MapDelete("/items/{id}", () => { });\n'
        )
        _setup_files(tmp_path, {"Program.cs": code})
        inventory = _make_inventory(["Program.cs"])
        profile = _make_profile({"dotnet-minimal-api": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 3
        methods = {s.method for s in surfaces}
        assert methods == {"GET", "POST", "DELETE"}

    def test_require_authorization(self, tmp_path: Path) -> None:
        code = 'app.MapGet("/secure", () => { }).RequireAuthorization();\n'
        _setup_files(tmp_path, {"Program.cs": code})
        inventory = _make_inventory(["Program.cs"])
        profile = _make_profile({"dotnet-minimal-api": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == "required"

    def test_skips_non_cs_files(self, tmp_path: Path) -> None:
        code = 'app.MapGet("/test", () => { });'
        _setup_files(tmp_path, {"Program.py": code})
        inventory = _make_inventory(["Program.py"])
        profile = _make_profile({"dotnet-minimal-api": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []


# ---------------------------------------------------------------------------
# .NET controller endpoint extraction
# ---------------------------------------------------------------------------


class TestDotnetControllerExtraction:
    """Extract endpoints from .NET controller attributes."""

    def test_basic_controller(self, tmp_path: Path) -> None:
        code = (
            "using Microsoft.AspNetCore.Mvc;\n\n"
            '[Route("api/[controller]")]\n'
            "public class UsersController : ControllerBase\n"
            "{\n"
            "    [HttpGet]\n"
            "    public IActionResult GetAll() => Ok();\n\n"
            "    [HttpPost]\n"
            "    public IActionResult Create() => Ok();\n"
            "}\n"
        )
        _setup_files(tmp_path, {"Controllers/UsersController.cs": code})
        inventory = _make_inventory(["Controllers/UsersController.cs"])
        profile = _make_profile({"aspnet": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 2
        get_surface = _find_surface(surfaces, "GET", "/api/users")
        assert get_surface is not None
        post_surface = _find_surface(surfaces, "POST", "/api/users")
        assert post_surface is not None

    def test_controller_with_sub_path(self, tmp_path: Path) -> None:
        code = (
            '[Route("api/[controller]")]\n'
            "public class ItemsController : ControllerBase\n"
            "{\n"
            '    [HttpGet("{id}")]\n'
            "    public IActionResult GetById(int id) => Ok();\n"
            "}\n"
        )
        _setup_files(tmp_path, {"Controllers/ItemsController.cs": code})
        inventory = _make_inventory(["Controllers/ItemsController.cs"])
        profile = _make_profile({"aspnet": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/api/items/{id}"

    def test_authorize_attribute(self, tmp_path: Path) -> None:
        code = (
            "[Authorize]\n"
            '[Route("api/[controller]")]\n'
            "public class SecureController : ControllerBase\n"
            "{\n"
            "    [HttpGet]\n"
            "    public IActionResult Get() => Ok();\n"
            "}\n"
        )
        _setup_files(tmp_path, {"Controllers/SecureController.cs": code})
        inventory = _make_inventory(["Controllers/SecureController.cs"])
        profile = _make_profile({"aspnet": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].auth == "required"

    def test_skips_non_controller_cs_files(self, tmp_path: Path) -> None:
        code = "[HttpGet]\npublic IActionResult Get() => Ok();"
        _setup_files(tmp_path, {"Services/UserService.cs": code})
        inventory = _make_inventory(["Services/UserService.cs"])
        profile = _make_profile({"aspnet": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []


# ---------------------------------------------------------------------------
# Next.js API route extraction
# ---------------------------------------------------------------------------


class TestNextjsApiExtraction:
    """Extract endpoints from Next.js API route files."""

    def test_pages_api_default_export(self, tmp_path: Path) -> None:
        code = (
            "export default function handler(req, res) {\n"
            "  res.status(200).json({ name: 'World' });\n"
            "}\n"
        )
        _setup_files(tmp_path, {"pages/api/hello.ts": code})
        inventory = _make_inventory(["pages/api/hello.ts"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].method == "ALL"
        assert surfaces[0].path == "/api/hello"

    def test_app_router_named_exports(self, tmp_path: Path) -> None:
        code = (
            "export async function GET(request: Request) {\n"
            "  return Response.json({ data: [] });\n"
            "}\n\n"
            "export async function POST(request: Request) {\n"
            "  return Response.json({ created: true });\n"
            "}\n"
        )
        _setup_files(tmp_path, {"app/api/items/route.ts": code})
        inventory = _make_inventory(["app/api/items/route.ts"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 2
        methods = {s.method for s in surfaces}
        assert methods == {"GET", "POST"}
        for s in surfaces:
            assert s.path == "/api/items"

    def test_dynamic_route_segment(self, tmp_path: Path) -> None:
        code = "export async function GET(req) { return Response.json({}); }"
        _setup_files(tmp_path, {"pages/api/users/[id].ts": code})
        inventory = _make_inventory(["pages/api/users/[id].ts"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/api/users/:id"

    def test_catch_all_route(self, tmp_path: Path) -> None:
        code = "export default function handler(req, res) { res.end(); }"
        _setup_files(tmp_path, {"pages/api/[...slug].ts": code})
        inventory = _make_inventory(["pages/api/[...slug].ts"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/api/:slug"

    def test_src_prefixed_api_routes(self, tmp_path: Path) -> None:
        code = "export async function GET() { return Response.json({}); }"
        _setup_files(tmp_path, {"src/app/api/health/route.ts": code})
        inventory = _make_inventory(["src/app/api/health/route.ts"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/api/health"

    def test_index_file_in_pages_api(self, tmp_path: Path) -> None:
        code = "export default function handler(req, res) { res.end(); }"
        _setup_files(tmp_path, {"pages/api/index.ts": code})
        inventory = _make_inventory(["pages/api/index.ts"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].path == "/api"

    def test_non_api_route_ignored(self, tmp_path: Path) -> None:
        code = "export default function Page() { return <div/>; }"
        _setup_files(tmp_path, {"pages/about.tsx": code})
        inventory = _make_inventory(["pages/about.tsx"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []

    def test_non_js_api_file_ignored(self, tmp_path: Path) -> None:
        _setup_files(tmp_path, {"pages/api/readme.md": "# API docs"})
        inventory = _make_inventory(["pages/api/readme.md"])
        profile = _make_profile({"nextjs": 0.8})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []


# ---------------------------------------------------------------------------
# Cross-framework: multiple frameworks detected
# ---------------------------------------------------------------------------


class TestMultipleFrameworks:
    """Test analyzer with multiple detected frameworks."""

    def test_express_and_nextjs(self, tmp_path: Path) -> None:
        _setup_files(
            tmp_path,
            {
                "server/routes.js": "app.get('/api/data', handler);",
                "pages/api/hello.ts": "export default function h(req, res) {}",
            },
        )
        inventory = _make_inventory(["server/routes.js", "pages/api/hello.ts"])
        profile = _make_profile({"express": 0.6, "nextjs": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 2
        methods_paths = {(s.method, s.path) for s in surfaces}
        assert ("GET", "/api/data") in methods_paths
        assert ("ALL", "/api/hello") in methods_paths

    def test_fastapi_and_flask(self, tmp_path: Path) -> None:
        _setup_files(
            tmp_path,
            {
                "api/main.py": "@app.get('/v1/items')\nasync def items(): pass",
                "web/views.py": "@app.route('/legacy')\ndef legacy(): pass",
            },
        )
        inventory = _make_inventory(["api/main.py", "web/views.py"])
        profile = _make_profile({"fastapi": 0.7, "flask": 0.5})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) >= 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_missing_file_handled_gracefully(self, tmp_path: Path) -> None:
        # File in inventory but not on disk
        inventory = _make_inventory(["nonexistent.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []

    def test_empty_file(self, tmp_path: Path) -> None:
        _setup_files(tmp_path, {"src/empty.py": ""})
        inventory = _make_inventory(["src/empty.py"])
        profile = _make_profile({"fastapi": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert surfaces == []

    def test_name_field_format(self, tmp_path: Path) -> None:
        code = "app.get('/test', handler);"
        _setup_files(tmp_path, {"src/app.js": code})
        inventory = _make_inventory(["src/app.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        assert surfaces[0].name == "GET /test"

    def test_to_dict_serialization(self, tmp_path: Path) -> None:
        code = "app.get('/test', handler);"
        _setup_files(tmp_path, {"src/app.js": code})
        inventory = _make_inventory(["src/app.js"])
        profile = _make_profile({"express": 0.7})

        surfaces = analyze_api_endpoints(tmp_path, inventory, profile)

        assert len(surfaces) == 1
        data = surfaces[0].to_dict()
        assert data["method"] == "GET"
        assert data["path"] == "/test"
        assert data["surface_type"] == "api"
        assert len(data["source_refs"]) == 1
