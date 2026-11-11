"""Tests for Blueprint / APIRouter prefix resolution (BEAN-081)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.apis import analyze_api_endpoints
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult


def _inv(paths: list[str]) -> InventoryResult:
    files = [
        FileEntry(path=p, size=1, extension=".py", hash="h", category="source")
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=len(files),
        total_skipped=0,
    )


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def _paths(root: Path, files: dict[str, str], stack: str) -> set[tuple[str, str]]:
    _write(root, files)
    prof = StackProfile(stacks={stack: 0.9}, evidence={}, signals=[])
    got = analyze_api_endpoints(root, _inv(list(files)), prof)
    return {(s.method, s.path) for s in got}


def test_flask_blueprint_url_prefix_and_register(tmp_path: Path) -> None:
    files = {
        "api/users.py": (
            "from flask import Blueprint\n"
            "bp = Blueprint('users', __name__, url_prefix='/users')\n"
            "@bp.get('/<int:uid>')\ndef one(uid): pass\n"
        ),
        "app.py": (
            "from flask import Flask\nfrom api.users import bp\n"
            "def create_app():\n    app = Flask(__name__)\n"
            "    app.register_blueprint(bp, url_prefix='/v1')\n    return app\n"
        ),
    }
    assert _paths(tmp_path, files, "flask") == {("GET", "/v1/users/<int:uid>")}


def test_fastapi_router_prefix_and_include(tmp_path: Path) -> None:
    files = {
        "routers/items.py": (
            "from fastapi import APIRouter\n"
            "router = APIRouter(prefix='/items')\n"
            "@router.get('/{item_id}')\nasync def one(item_id: int): ...\n"
        ),
        "main.py": (
            "from fastapi import FastAPI\nfrom routers import items\n"
            "app = FastAPI()\napp.include_router(items.router, prefix='/api')\n"
        ),
    }
    assert _paths(tmp_path, files, "fastapi") == {("GET", "/api/items/{item_id}")}


def test_no_prefix_is_unchanged(tmp_path: Path) -> None:
    files = {
        "app.py": "from flask import Flask\napp = Flask(__name__)\n@app.get('/x')\ndef x(): pass\n"
    }
    assert _paths(tmp_path, files, "flask") == {("GET", "/x")}
