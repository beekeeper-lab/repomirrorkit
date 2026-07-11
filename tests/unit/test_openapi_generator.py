"""Tests for the OpenAPI 3.1 contract generator (BEAN-071)."""

from __future__ import annotations

import json
from pathlib import Path

from openapi_spec_validator import validate

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.generator.openapi import (
    generate_openapi_contract,
    normalize_path,
)


def _api(
    method: str,
    path: str,
    request_schema: dict | None = None,
    response_schema: dict | None = None,
    auth: str = "",
) -> ApiSurface:
    return ApiSurface(
        name=f"{method} {path}",
        method=method,
        path=path,
        auth=auth,
        request_schema=request_schema or {},
        response_schema=response_schema or {},
        source_refs=[SourceRef(file_path="app.py", start_line=1)],
    )


def _generate(tmp_path: Path, *apis: ApiSurface) -> dict:
    surfaces = SurfaceCollection(apis=list(apis))
    path = generate_openapi_contract(surfaces, tmp_path, "sample")
    assert path is not None
    return json.loads(path.read_text())


class TestNormalizePath:
    def test_flask_converter_segments(self) -> None:
        assert normalize_path("/users/<int:user_id>") == "/users/{user_id}"
        assert normalize_path("/files/<path:name>") == "/files/{name}"
        assert normalize_path("/tags/<slug>") == "/tags/{slug}"

    def test_express_params(self) -> None:
        assert normalize_path("/users/:id/posts/:postId") == (
            "/users/{id}/posts/{postId}"
        )

    def test_openapi_template_passthrough(self) -> None:
        assert normalize_path("/orders/{order_id}") == "/orders/{order_id}"


class TestContractGeneration:
    def test_no_apis_returns_none(self, tmp_path: Path) -> None:
        assert generate_openapi_contract(SurfaceCollection(), tmp_path, "x") is None

    def test_document_validates_as_openapi_31(self, tmp_path: Path) -> None:
        doc = _generate(
            tmp_path,
            _api(
                "POST",
                "/api/users",
                request_schema={
                    "fields": [
                        {
                            "name": "name",
                            "type": "unknown",
                            "required": True,
                            "source": "body",
                        },
                        {
                            "name": "email",
                            "type": "str",
                            "required": False,
                            "source": "body",
                        },
                    ],
                    "confidence": "inferred",
                },
                response_schema={
                    "fields": [
                        {
                            "name": "id",
                            "type": "integer",
                            "required": True,
                            "source": "body",
                        }
                    ],
                    "confidence": "inferred",
                },
            ),
            _api("GET", "/api/users", auth="required"),
        )
        validate(doc)  # raises on an invalid document
        assert doc["openapi"] == "3.1.0"

    def test_populated_contract_round_trips_fields(self, tmp_path: Path) -> None:
        doc = _generate(
            tmp_path,
            _api(
                "POST",
                "/orders",
                request_schema={
                    "fields": [
                        {
                            "name": "sku",
                            "type": "str",
                            "required": True,
                            "source": "body",
                        },
                        {
                            "name": "quantity",
                            "type": "int",
                            "required": True,
                            "source": "body",
                        },
                    ],
                    "confidence": "declared",
                },
                response_schema={
                    "fields": [
                        {
                            "name": "id",
                            "type": "int",
                            "required": True,
                            "source": "body",
                        }
                    ],
                    "confidence": "declared",
                },
            ),
        )
        op = doc["paths"]["/orders"]["post"]
        body = op["requestBody"]["content"]["application/json"]["schema"]
        assert body["properties"]["sku"] == {"type": "string"}
        assert body["properties"]["quantity"] == {"type": "integer"}
        assert set(body["required"]) == {"sku", "quantity"}
        resp = op["responses"]["201"]["content"]["application/json"]["schema"]
        assert resp["properties"]["id"] == {"type": "integer"}
        assert op["x-harvester-confidence"] == "declared"
        assert "x-harvester-gap" not in op

    def test_query_and_path_params_split_from_body(self, tmp_path: Path) -> None:
        doc = _generate(
            tmp_path,
            _api(
                "GET",
                "/orders/{order_id}",
                request_schema={
                    "fields": [
                        {
                            "name": "order_id",
                            "type": "int",
                            "required": True,
                            "source": "path_or_query",
                        },
                        {
                            "name": "verbose",
                            "type": "bool",
                            "required": False,
                            "source": "path_or_query",
                        },
                    ],
                    "confidence": "declared",
                },
            ),
        )
        params = {
            p["name"]: p
            for p in doc["paths"]["/orders/{order_id}"]["get"]["parameters"]
        }
        assert params["order_id"]["in"] == "path"
        assert params["order_id"]["required"] is True
        assert params["verbose"]["in"] == "query"
        assert params["verbose"]["required"] is False

    def test_unknown_contracts_carry_gap_extension(self, tmp_path: Path) -> None:
        doc = _generate(
            tmp_path,
            _api(
                "POST",
                "/opaque",
                request_schema={"unknown": True},
                response_schema={"unknown": True},
            ),
        )
        op = doc["paths"]["/opaque"]["post"]
        assert op["x-harvester-gap"] is True
        assert op["responses"]["201"]["description"] == "Unknown (gap)"

    def test_auth_surface_gets_security_scheme(self, tmp_path: Path) -> None:
        doc = _generate(tmp_path, _api("GET", "/private", auth="required"))
        op = doc["paths"]["/private"]["get"]
        assert op["security"] == [{"harvestedAuth": []}]
        assert "harvestedAuth" in doc["components"]["securitySchemes"]

    def test_gap_count_visible_not_silent(self, tmp_path: Path) -> None:
        surfaces = SurfaceCollection(apis=[_api("POST", "/a"), _api("GET", "/b")])
        path = generate_openapi_contract(surfaces, tmp_path, "x")
        assert path is not None
        doc = json.loads(path.read_text())
        gaps = [
            op
            for methods in doc["paths"].values()
            for op in methods.values()
            if op.get("x-harvester-gap")
        ]
        assert len(gaps) == 2
