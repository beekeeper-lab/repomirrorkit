"""Tests for Python API contract extraction (BEAN-062)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.api_contracts import (
    populate_python_api_contracts,
)
from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface, SourceRef


def _write(tmp_path: Path, rel: str, content: str) -> None:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _surface(method: str, path: str, file_path: str, line: int) -> ApiSurface:
    return ApiSurface(
        name=f"{method} {path}",
        method=method,
        path=path,
        source_refs=[SourceRef(file_path=file_path, start_line=line)],
    )


FLASK_APP = """\
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/api/items", methods=["POST"])
def create_item():
    data = request.get_json()
    name = data["name"]
    tag = data.get("tag")
    return jsonify({"id": 1, "name": name}), 201


@app.route("/api/items", methods=["GET"])
def list_items():
    page = request.args.get("page")
    return jsonify([{"id": 1, "name": "x"}])
"""


class TestFlaskExtraction:
    def test_post_request_fields_inferred(self, tmp_path: Path) -> None:
        _write(tmp_path, "app.py", FLASK_APP)
        surface = _surface("POST", "/api/items", "app.py", 6)

        populated = populate_python_api_contracts([surface], tmp_path)

        assert populated == 1
        fields = {f["name"]: f for f in surface.request_schema["fields"]}
        assert fields["name"]["required"] is True
        assert fields["name"]["source"] == "body"
        assert fields["tag"]["required"] is False
        assert surface.request_schema["confidence"] == "inferred"

    def test_post_response_fields_from_jsonify(self, tmp_path: Path) -> None:
        _write(tmp_path, "app.py", FLASK_APP)
        surface = _surface("POST", "/api/items", "app.py", 6)

        populate_python_api_contracts([surface], tmp_path)

        fields = {f["name"]: f for f in surface.response_schema["fields"]}
        assert fields["id"]["type"] == "integer"
        assert "name" in fields

    def test_get_query_params_and_listcomp_response(self, tmp_path: Path) -> None:
        _write(tmp_path, "app.py", FLASK_APP)
        surface = _surface("GET", "/api/items", "app.py", 14)

        populate_python_api_contracts([surface], tmp_path)

        fields = {f["name"]: f for f in surface.request_schema["fields"]}
        assert fields["page"]["source"] == "query"
        assert fields["page"]["required"] is False
        resp = {f["name"] for f in surface.response_schema["fields"]}
        assert resp == {"id", "name"}

    def test_uninferable_body_marked_unknown(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "app.py",
            '@app.route("/x", methods=["POST"])\ndef opaque():\n    return process()\n',
        )
        surface = _surface("POST", "/x", "app.py", 1)

        populated = populate_python_api_contracts([surface], tmp_path)

        assert populated == 0
        assert surface.request_schema == {"unknown": True}
        assert surface.response_schema == {"unknown": True}

    def test_get_with_no_inputs_is_empty_not_unknown(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "app.py",
            '@app.route("/ping")\ndef ping():\n    return make_response()\n',
        )
        surface = _surface("GET", "/ping", "app.py", 1)

        populate_python_api_contracts([surface], tmp_path)

        assert surface.request_schema == {"fields": [], "confidence": "inferred"}
        assert surface.response_schema == {"unknown": True, "status": 200}


FASTAPI_APP = """\
from fastapi import FastAPI
from schemas import OrderIn, OrderOut

app = FastAPI()


@app.post("/orders", response_model=OrderOut)
def create_order(order: OrderIn):
    return save(order)


@app.get("/orders/{order_id}")
def get_order(order_id: int, verbose: bool = False) -> OrderOut:
    return load(order_id)
"""

FASTAPI_SCHEMAS = """\
from pydantic import BaseModel


class OrderIn(BaseModel):
    sku: str
    quantity: int
    note: str | None = None


class OrderOut(BaseModel):
    id: int
    sku: str
    status: str
"""


class TestFastAPIExtraction:
    def test_pydantic_body_param_expands_declared(self, tmp_path: Path) -> None:
        _write(tmp_path, "main.py", FASTAPI_APP)
        _write(tmp_path, "schemas.py", FASTAPI_SCHEMAS)
        surface = _surface("POST", "/orders", "main.py", 7)

        populated = populate_python_api_contracts([surface], tmp_path)

        assert populated == 1
        assert surface.request_schema["confidence"] == "declared"
        fields = {f["name"]: f for f in surface.request_schema["fields"]}
        assert fields["sku"] == {
            "name": "sku",
            "type": "str",
            "required": True,
            "source": "body",
        }
        assert fields["quantity"]["type"] == "int"
        assert fields["note"]["required"] is False

    def test_response_model_kwarg_expands(self, tmp_path: Path) -> None:
        _write(tmp_path, "main.py", FASTAPI_APP)
        _write(tmp_path, "schemas.py", FASTAPI_SCHEMAS)
        surface = _surface("POST", "/orders", "main.py", 7)

        populate_python_api_contracts([surface], tmp_path)

        fields = {f["name"]: f for f in surface.response_schema["fields"]}
        assert set(fields) == {"id", "sku", "status"}
        assert surface.response_schema["confidence"] == "declared"

    def test_primitive_params_and_return_annotation(self, tmp_path: Path) -> None:
        _write(tmp_path, "main.py", FASTAPI_APP)
        _write(tmp_path, "schemas.py", FASTAPI_SCHEMAS)
        surface = _surface("GET", "/orders/{order_id}", "main.py", 12)

        populate_python_api_contracts([surface], tmp_path)

        fields = {f["name"]: f for f in surface.request_schema["fields"]}
        assert fields["order_id"]["required"] is True
        assert fields["order_id"]["source"] == "path_or_query"
        assert fields["verbose"]["required"] is False
        resp = {f["name"] for f in surface.response_schema["fields"]}
        assert resp == {"id", "sku", "status"}

    def test_unresolvable_response_model_keeps_type_name(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "main.py",
            "@app.post('/x', response_model=Mystery)\n"
            "def make(payload: Mystery):\n"
            "    return payload\n",
        )
        surface = _surface("POST", "/x", "main.py", 1)

        populate_python_api_contracts([surface], tmp_path)

        assert surface.response_schema["type"] == "Mystery"
        assert surface.request_schema == {"unknown": True}


class TestNonPythonAndEdgeCases:
    def test_non_python_surfaces_untouched(self, tmp_path: Path) -> None:
        surface = _surface("GET", "/js", "routes/index.ts", 3)

        populated = populate_python_api_contracts([surface], tmp_path)

        assert populated == 0
        assert surface.request_schema == {}
        assert surface.response_schema == {}

    def test_missing_file_marks_unknown(self, tmp_path: Path) -> None:
        surface = _surface("POST", "/gone", "missing.py", 1)

        populate_python_api_contracts([surface], tmp_path)

        assert surface.request_schema == {"unknown": True}
        assert surface.response_schema == {"unknown": True}

    def test_syntax_error_file_marks_unknown(self, tmp_path: Path) -> None:
        _write(tmp_path, "bad.py", "def broken(:\n")
        surface = _surface("POST", "/bad", "bad.py", 1)

        populate_python_api_contracts([surface], tmp_path)

        assert surface.request_schema == {"unknown": True}
        assert surface.response_schema == {"unknown": True}


FLASK_FACTORY = """\
from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)

    @app.post("/api/users")
    def create_user():
        data = request.get_json()
        name = data["name"]
        return jsonify({"id": 1, "name": name}), 201

    return app
"""


class TestFlaskShorthandContracts:
    def test_shorthand_in_factory_is_flask_not_fastapi(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/app.py", FLASK_FACTORY)
        surface = _surface("POST", "/api/users", "src/app.py", 7)

        populated = populate_python_api_contracts([surface], tmp_path)

        assert populated == 1
        fields = {f["name"]: f for f in surface.request_schema["fields"]}
        assert fields["name"]["required"] is True
        assert surface.request_schema["confidence"] == "inferred"


FLASK_STATUS_APP = """\
from flask import abort, jsonify, request


def create_app():
    def unauthorized():
        return jsonify({"error": "unauthorized"}), 401

    def transition(order_id, target):
        if not request.headers.get("X-API-Key"):
            return unauthorized()
        if order_id > 100:
            return jsonify({"error": "not found"}), 404
        return jsonify({"id": order_id, "status": target})

    @app.post("/orders")
    def create():
        data = request.get_json()
        if not data:
            return jsonify({"error": "invalid json"}), 400
        if "customer" not in data:
            abort(422)
        return jsonify({"id": 1}), 201

    @app.post("/orders/<int:order_id>/pay")
    def pay(order_id):
        return transition(order_id, "paid")
"""


class TestFlaskStatusAndErrors:
    def test_statuses_and_error_messages_follow_helpers(self, tmp_path: Path) -> None:
        _write(tmp_path, "app.py", FLASK_STATUS_APP)
        create = _surface("POST", "/orders", "app.py", 16)
        pay = _surface("POST", "/orders/<int:order_id>/pay", "app.py", 26)

        populate_python_api_contracts([create, pay], tmp_path)

        assert create.response_schema["status"] == 201
        assert {"status": 400, "message": "invalid json"} in create.response_schema[
            "errors"
        ]
        assert {"status": 422} in create.response_schema["errors"]
        assert pay.response_schema["status"] == 200
        errs = {e["status"]: e.get("message") for e in pay.response_schema["errors"]}
        assert errs == {401: "unauthorized", 404: "not found"}


FLASK_VALIDATION_APP = """\
from flask import jsonify, request


@app.post("/orders")
def create():
    data = request.get_json(silent=True)
    customer = data.get("customer")
    if not isinstance(customer, str) or len(customer.strip()) < 2:
        return jsonify({"error": "customer must be at least 2 characters"}), 400
    qty = data.get("qty")
    if not isinstance(qty, int) or qty < 1 or qty > 99:
        return jsonify({"error": "bad qty"}), 400
    category_id = data.get("category_id")
    if db.session.get(Category, category_id) is None:
        return jsonify({"error": "unknown category"}), 400
    note = data.get("note")
    return jsonify({"id": 1, "customer": customer}), 201
"""


class TestImperativeValidation:
    def test_guards_become_types_required_and_rules(self, tmp_path: Path) -> None:
        _write(tmp_path, "app.py", FLASK_VALIDATION_APP)
        surface = _surface("POST", "/orders", "app.py", 5)

        populate_python_api_contracts([surface], tmp_path)

        f = {x["name"]: x for x in surface.request_schema["fields"]}
        assert f["customer"]["type"] == "string" and f["customer"]["required"] is True
        assert f["customer"]["rules"] == ["min_length=2"]
        assert f["qty"]["type"] == "integer" and set(f["qty"]["rules"]) == {
            "min=1",
            "max=99",
        }
        assert f["category_id"]["required"] is True
        assert f["category_id"]["rules"] == ["references=Category"]
        assert f["note"]["required"] is False and "rules" not in f["note"]
        # error payloads are not success-response fields
        assert {x["name"] for x in surface.response_schema["fields"]} == {
            "id",
            "customer",
        }
        assert surface.response_schema["status"] == 201
