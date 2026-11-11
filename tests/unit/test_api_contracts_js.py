"""Tests for JS/TS API contract extraction (BEAN-063)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.api_contracts_js import (
    populate_js_api_contracts,
)
from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface, SourceRef


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _surface(method: str, path: str, file: str, line: int) -> ApiSurface:
    return ApiSurface(
        name=f"{method} {path}",
        method=method,
        path=path,
        source_refs=[SourceRef(file_path=file, start_line=line)],
    )


def _fields(schema: dict, source: str | None = None) -> dict[str, dict]:
    return {
        f["name"]: f
        for f in schema["fields"]
        if source is None or f["source"] == source
    }


# ---------------------------------------------------------------- Next.js


def test_next_typed_body_and_response_status(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "models/user.ts",
        "export interface CreateUser { name: string; email?: string }\n"
        "export interface User { id: number; name: string }\n",
    )
    _write(
        tmp_path,
        "app/api/users/route.ts",
        'import { NextResponse } from "next/server";\n'
        'import type { CreateUser, User } from "../../../models/user";\n'
        "export async function POST(request: Request) {\n"
        "  const body: CreateUser = await request.json();\n"
        "  if (!body.name) {\n"
        '    return NextResponse.json({ error: "name required" }, { status: 400 });\n'
        "  }\n"
        "  const user: User = { id: 1, name: body.name };\n"
        "  return NextResponse.json(user, { status: 201 });\n"
        "}\n",
    )
    s = _surface("POST", "/api/users", "app/api/users/route.ts", 3)
    assert populate_js_api_contracts([s], tmp_path) == 1
    req = _fields(s.request_schema)
    assert s.request_schema["confidence"] == "declared"
    assert req["name"]["required"] is True and req["name"]["type"] == "string"
    assert req["email"]["required"] is False
    assert s.response_schema["status"] == 201
    assert {"id", "name"} == set(_fields(s.response_schema))
    assert s.response_schema["errors"] == [{"status": 400, "message": "name required"}]


def test_next_dynamic_route_params_and_query(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "app/api/users/[id]/route.ts",
        "export async function GET(request: Request, { params }: { params: { id: string } }) {\n"
        "  const q = new URL(request.url).searchParams.get('verbose');\n"
        "  return Response.json({ id: params.id, verbose: q });\n"
        "}\n",
    )
    s = _surface("GET", "/api/users/:id", "app/api/users/[id]/route.ts", 1)
    populate_js_api_contracts([s], tmp_path)
    req = s.request_schema["fields"]
    by = {(f["source"], f["name"]): f for f in req}
    assert by[("path", "id")]["type"] == "string" and by[("path", "id")]["required"]
    assert by[("query", "verbose")]["required"] is False


# ---------------------------------------------------------------- Express


EXPRESS = """\
const express = require('express');
const app = express();

app.post('/items', (req, res) => {
  const { name, price = 0 } = req.body;
  const tag = req.query.tag;
  res.status(201).json({ id: 1, name, price });
});

app.get('/items', (req, res) => {
  res.json([{ id: 1, name: 'x' }]);
});
"""


def test_express_destructured_body_and_status(tmp_path: Path) -> None:
    _write(tmp_path, "server.js", EXPRESS)
    post = _surface("POST", "/items", "server.js", 4)
    get = _surface("GET", "/items", "server.js", 10)
    assert populate_js_api_contracts([post, get], tmp_path) == 2
    body = _fields(post.request_schema, "body")
    assert body["name"]["required"] is True
    assert body["price"]["required"] is False
    assert _fields(post.request_schema, "query")["tag"]["required"] is False
    assert post.response_schema["status"] == 201
    assert get.response_schema["is_array"] is True
    assert set(_fields(get.response_schema)) == {"id", "name"}
    assert get.request_schema == {"fields": [], "confidence": "inferred"}


# ---------------------------------------------------------------- zod


def test_zod_schema_drives_request_with_rules(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "api.ts",
        "import { z } from 'zod';\n"
        "const CreateOrder = z.object({\n"
        "  sku: z.string().min(3),\n"
        "  qty: z.number().int().positive(),\n"
        "  note: z.string().optional(),\n"
        "});\n"
        "app.post('/orders', async (req, res) => {\n"
        "  const data = CreateOrder.parse(req.body);\n"
        "  res.json({ ok: true });\n"
        "});\n",
    )
    s = _surface("POST", "/orders", "api.ts", 7)
    populate_js_api_contracts([s], tmp_path)
    assert s.request_schema["confidence"] == "declared"
    f = _fields(s.request_schema)
    assert f["sku"]["required"] and any("min(3)" in r for r in f["sku"]["rules"])
    assert f["qty"]["type"] == "number"
    assert f["note"]["required"] is False


# ---------------------------------------------------------------- NestJS


NEST = """\
import { Controller, Get, Post, Body, Param, Query } from '@nestjs/common';
import { IsEmail, IsOptional, IsString } from 'class-validator';

export class CreateCatDto {
  @IsString() name: string;
  @IsEmail() email: string;
  @IsOptional() age?: number;
}

export interface Cat { id: number; name: string }

@Controller('cats')
export class CatsController {
  @Post()
  create(@Body() dto: CreateCatDto): Cat {
    return { id: 1, name: dto.name };
  }

  @Get(':id')
  findOne(@Param('id') id: string, @Query('expand') expand?: string): Promise<Cat> {
    return this.svc.find(id);
  }
}
"""


def test_nest_dto_param_and_return_types(tmp_path: Path) -> None:
    _write(tmp_path, "cats.controller.ts", NEST)
    post = _surface("POST", "/cats", "cats.controller.ts", 14)
    get = _surface("GET", "/cats/:id", "cats.controller.ts", 19)
    assert populate_js_api_contracts([post, get], tmp_path) == 2
    req = _fields(post.request_schema)
    assert req["name"]["rules"] == ["IsString()"]
    assert req["age"]["required"] is False
    assert post.response_schema["confidence"] == "declared"
    assert set(_fields(post.response_schema)) == {"id", "name"}
    by = {(f["source"], f["name"]) for f in get.request_schema["fields"]}
    assert ("path", "id") in by and ("query", "expand") in by
    assert set(_fields(get.response_schema)) == {"id", "name"}


# ---------------------------------------------------------------- edges


def test_python_and_missing_files_untouched_or_unknown(tmp_path: Path) -> None:
    py = _surface("GET", "/x", "app.py", 1)
    missing = _surface("POST", "/y", "nope.ts", 1)
    populate_js_api_contracts([py, missing], tmp_path)
    assert py.request_schema == {} and py.response_schema == {}
    assert missing.request_schema == {"unknown": True}
    assert missing.response_schema == {"unknown": True}


def test_handler_without_inferable_body_is_unknown(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "r.ts",
        "export async function POST(request: Request) {\n  return handle(request);\n}\n",
    )
    s = _surface("POST", "/r", "r.ts", 1)
    populate_js_api_contracts([s], tmp_path)
    assert s.request_schema == {"unknown": True}


def test_handler_factory_with_status_and_error_messages(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "server.js",
        "function transition(allowed, target) {\n"
        "  return (req, res) => {\n"
        "    if (!req.get('X-API-Key')) return res.status(401).json({ error: 'unauthorized' });\n"
        "    const order = find(req.params.id);\n"
        "    if (!order) return res.status(404).json({ error: 'not found' });\n"
        "    if (!allowed.includes(order.status)) {\n"
        "      return res.status(409).json({ error: 'invalid transition' });\n"
        "    }\n"
        "    res.json(order);\n"
        "  };\n"
        "}\n"
        "app.post('/orders/:id/pay', transition(['submitted'], 'paid'));\n",
    )
    s = _surface("POST", "/orders/:id/pay", "server.js", 12)
    populate_js_api_contracts([s], tmp_path)
    errs = {e["status"]: e.get("message") for e in s.response_schema["errors"]}
    assert errs == {401: "unauthorized", 404: "not found", 409: "invalid transition"}
    assert ("path", "id") in {
        (f["source"], f["name"]) for f in s.request_schema["fields"]
    }
