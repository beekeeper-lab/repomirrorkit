"""OpenAPI 3.1 contract generation from API surfaces (BEAN-071).

Emits ``<out>/api-contract.json`` — a machine-readable, framework-neutral
API contract a rebuild agent (or contract-test tooling) can consume
directly. Every discovered API surface becomes a path+method operation.

Design decisions:

- **JSON, not YAML.** OpenAPI 3.1 is JSON-native and every validator and
  code generator accepts it; emitting JSON avoids adding a YAML dependency
  (dependency-discipline rule). A YAML rendering can ride along once
  PyYAML lands for the screen specs (BEAN-073).
- **Gaps are visible, never fabricated.** Surfaces whose contracts could
  not be extracted (``{"unknown": true}`` markers from BEAN-062, or
  stacks without contract extraction yet) get an empty schema plus an
  ``x-harvester-gap: true`` extension so consumers can filter or flag
  them. Field-level confidence is carried as ``x-harvester-confidence``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers import SurfaceCollection
from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface

logger = structlog.get_logger()

# Flask/Werkzeug converter segments: /users/<int:user_id> → /users/{user_id}
_FLASK_SEGMENT_RE = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")
# Express-style params: /users/:id → /users/{id}
_EXPRESS_SEGMENT_RE = re.compile(r":(\w+)")

# Python annotation text → OpenAPI type
_TYPE_MAP: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "bytes": "string",
    "datetime": "string",
    "date": "string",
    "UUID": "string",
    "Decimal": "number",
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
    "null": "null",
}


def normalize_path(path: str) -> str:
    """Normalize framework path syntax to OpenAPI ``{param}`` templates."""
    path = _FLASK_SEGMENT_RE.sub(r"{\1}", path)
    path = _EXPRESS_SEGMENT_RE.sub(r"{\1}", path)
    if not path.startswith("/"):
        path = "/" + path
    return path


def _openapi_type(raw: str) -> dict[str, Any]:
    """Map an extracted field type to an OpenAPI schema fragment."""
    cleaned = raw.strip()
    if cleaned.startswith("Optional[") and cleaned.endswith("]"):
        cleaned = cleaned[9:-1]
    cleaned = cleaned.removesuffix("| None").removesuffix("|None").strip()
    mapped = _TYPE_MAP.get(cleaned)
    if mapped is None:
        return {}  # unknown type — permissive empty schema
    return {"type": mapped}


def _fields_to_object_schema(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an OpenAPI object schema from extracted contract fields."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in fields:
        name = str(field.get("name", ""))
        if not name:
            continue
        properties[name] = _openapi_type(str(field.get("type", "")))
        if field.get("required"):
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _split_request_fields(
    schema: dict[str, Any], path_template: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split request fields into (parameters, body fields)."""
    params: list[dict[str, Any]] = []
    body: list[dict[str, Any]] = []
    path_params = set(re.findall(r"\{(\w+)\}", path_template))
    for field in schema.get("fields", []):
        source = field.get("source", "")
        name = str(field.get("name", ""))
        if source in ("query", "path_or_query") or (
            source not in ("body", "form") and name in path_params
        ):
            location = "path" if name in path_params else "query"
            param: dict[str, Any] = {
                "name": name,
                "in": location,
                "required": True if location == "path" else bool(field.get("required")),
                "schema": _openapi_type(str(field.get("type", ""))),
            }
            params.append(param)
        else:
            body.append(field)
    return params, body


def _build_operation(surface: ApiSurface, path_template: str) -> dict[str, Any]:
    """Build a single OpenAPI operation object from an API surface."""
    operation: dict[str, Any] = {
        "summary": surface.name,
        "responses": {},
    }

    request = surface.request_schema or {}
    response = surface.response_schema or {}
    confidence = request.get("confidence") or response.get("confidence")
    if confidence:
        operation["x-harvester-confidence"] = confidence

    gap = False

    if request.get("unknown") is True:
        gap = True
    elif "fields" in request:
        params, body_fields = _split_request_fields(request, path_template)
        if params:
            operation["parameters"] = params
        if body_fields:
            operation["requestBody"] = {
                "required": any(f.get("required") for f in body_fields),
                "content": {
                    "application/json": {
                        "schema": _fields_to_object_schema(body_fields)
                    }
                },
            }
    elif not request:
        gap = True

    success_code = "201" if surface.method == "POST" else "200"
    if response.get("unknown") is True:
        gap = True
        operation["responses"][success_code] = {"description": "Unknown (gap)"}
    elif response.get("fields"):
        operation["responses"][success_code] = {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": _fields_to_object_schema(response["fields"])
                }
            },
        }
    elif "type" in response:
        operation["responses"][success_code] = {
            "description": f"Success ({response['type']})",
        }
    else:
        gap = True
        operation["responses"][success_code] = {"description": "Unknown (gap)"}

    if gap:
        operation["x-harvester-gap"] = True
    if surface.auth:
        operation["security"] = [{"harvestedAuth": []}]

    return operation


def generate_openapi_contract(
    surfaces: SurfaceCollection,
    output_dir: Path,
    project_name: str,
) -> Path | None:
    """Generate ``api-contract.json`` at the harvest output root.

    Args:
        surfaces: All extracted surfaces (APIs are consumed).
        output_dir: Harvest output root directory.
        project_name: Analyzed project name (contract title).

    Returns:
        Path to the written contract, or None when no API surfaces exist.
    """
    apis = list(surfaces.apis)
    if not apis:
        logger.info("openapi_skipped_no_apis")
        return None

    paths: dict[str, dict[str, Any]] = {}
    any_auth = False
    gap_count = 0

    for surface in apis:
        template = normalize_path(surface.path or "/")
        method = (surface.method or "GET").lower()
        operation = _build_operation(surface, template)
        if operation.get("x-harvester-gap"):
            gap_count += 1
        if surface.auth:
            any_auth = True
        paths.setdefault(template, {})[method] = operation

    document: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": f"{project_name} — harvested API contract",
            "version": "0.0.0-harvested",
            "description": (
                "Generated by RepoMirrorKit from source analysis. Operations "
                "marked x-harvester-gap could not be fully extracted and "
                "need verification against the original application."
            ),
        },
        "paths": paths,
    }
    if any_auth:
        document["components"] = {
            "securitySchemes": {
                "harvestedAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "Placeholder scheme — the original app requires "
                        "authentication here; the exact mechanism is in the "
                        "auth surfaces/beans."
                    ),
                }
            }
        }

    contract_path = output_dir / "api-contract.json"
    contract_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    logger.info(
        "openapi_contract_written",
        path=str(contract_path),
        operations=sum(len(ops) for ops in paths.values()),
        gaps=gap_count,
    )
    return contract_path
