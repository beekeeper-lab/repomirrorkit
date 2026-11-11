"""Tests for business-rule mining (BEAN-065)."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.analyzers.business_rules import (
    analyze_business_rules,
    neutral_rule,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ModelField,
    ModelSurface,
    ScreenField,
    ScreenSurface,
    SurfaceCollection,
)


@pytest.mark.parametrize(
    ("raw", "ftype", "expected"),
    [
        (".min(3)", "string", "minimum length 3"),
        (".min(1)", "number", "minimum value 1"),
        ("MinLength(8)", "string", "minimum length 8"),
        ("IsEmail()", "string", "must be a valid email address"),
        ("minLength=2", "text", "minimum length 2"),
        ("ge=1", "int", "minimum value 1"),
        ("max_length=80", "str", "maximum length 80"),
        (".int()", "number", "must be an integer"),
        (".positive()", "number", "must be positive"),
        ("required", "", "required"),
        ("IsString()", "string", None),
        (".optional()", "string", None),
    ],
)
def test_neutral_rule_translation(raw: str, ftype: str, expected: str | None) -> None:
    assert neutral_rule(raw, ftype) == expected


def test_rules_from_api_screen_model_and_auth() -> None:
    api = ApiSurface(
        name="POST /api/orders",
        method="POST",
        path="/api/orders",
        auth="required",
        request_schema={
            "fields": [
                {
                    "name": "qty",
                    "type": "number",
                    "required": True,
                    "source": "body",
                    "rules": [".int()", ".positive()"],
                }
            ],
            "confidence": "declared",
        },
    )
    screen = ScreenSurface(
        name="OrderForm",
        screen_name="OrderForm",
        fields=[
            ScreenField(
                name="qty",
                input_type="number",
                required=True,
                validation=["required", "min=1"],
            )
        ],
    )
    model = ModelSurface(
        name="Order",
        entity_name="Order",
        fields=[
            ModelField(
                name="sku",
                field_type="str",
                constraints=["not_null", "unique", "max_length=20"],
            )
        ],
    )
    coll = SurfaceCollection(apis=[api], screens=[screen], models=[model])

    rules = analyze_business_rules(coll)

    by_kind = {r.rule_kind for r in rules}
    assert by_kind == {"validation", "permission", "invariant"}
    exprs = {r.expression for r in rules}
    assert "POST /api/orders body field 'qty': must be an integer" in exprs
    assert "POST /api/orders: authentication required" in exprs
    assert "screen OrderForm field 'qty': minimum value 1" in exprs
    assert "Order.sku: must be unique" in exprs
    assert "Order.sku: maximum length 20" in exprs
    names = (
        {a.name for a in coll.apis}
        | {s.name for s in coll.screens}
        | {m.name for m in coll.models}
    )
    assert all(set(r.applies_to) <= names and r.applies_to for r in rules)


def test_duplicates_collapsed() -> None:
    model = ModelSurface(
        name="U",
        entity_name="U",
        fields=[
            ModelField(name="a", field_type="str", constraints=["unique", "unique"])
        ],
    )
    assert len(analyze_business_rules(SurfaceCollection(models=[model]))) == 1
