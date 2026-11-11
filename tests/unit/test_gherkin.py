"""Tests for Gherkin generation (BEAN-074)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from gherkin.parser import Parser

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    BusinessRuleSurface,
    ModelField,
    ModelSurface,
    ScreenAction,
    ScreenField,
    ScreenSurface,
    SurfaceCollection,
    WorkflowSurface,
    WorkflowTransition,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.features import (
    cluster_surfaces,
    write_features_and_manifest,
)
from repo_mirror_kit.harvester.generator.gherkin import generate_gherkin

FORBIDDEN = re.compile(
    r"css|selector|<div|usestate|\.tsx|\.py\b|import |@app\.|flask|express|react|nextjs|sqlalchemy|getelementby",
    re.IGNORECASE,
)


def _collection() -> SurfaceCollection:
    api = ApiSurface(
        name="POST /api/orders",
        method="POST",
        path="/api/orders",
        auth="required",
        request_schema={
            "fields": [
                {
                    "name": "customer",
                    "type": "string",
                    "required": True,
                    "source": "body",
                }
            ],
            "confidence": "declared",
        },
        response_schema={
            "fields": [
                {"name": "id", "type": "integer", "required": True, "source": "body"}
            ],
            "confidence": "declared",
            "status": 201,
            "errors": [{"status": 400}],
        },
    )
    pay = ApiSurface(
        name="POST /api/orders/<int:order_id>/pay",
        method="POST",
        path="/api/orders/<int:order_id>/pay",
    )
    model = ModelSurface(
        name="Order",
        entity_name="Order",
        fields=[ModelField("email", "str", ["unique", "not_null"])],
    )
    wf = WorkflowSurface(
        name="OrderStatus lifecycle",
        entity_ref="OrderStatus",
        states=["DRAFT", "PAID", "SHIPPED"],
        confidence="declared",
        transitions=[
            WorkflowTransition(
                "DRAFT",
                "PAID",
                trigger="pay",
                trigger_ref="POST /api/orders/<int:order_id>/pay",
            ),
            WorkflowTransition("PAID", "SHIPPED", trigger="ship"),
        ],
    )
    rules = [
        BusinessRuleSurface(
            name="r1",
            rule_kind="validation",
            expression="POST /api/orders body field 'customer': minimum length 3",
            applies_to=["POST /api/orders"],
            confidence="declared",
        ),
        BusinessRuleSurface(
            name="r2",
            rule_kind="permission",
            expression="POST /api/orders: authentication required",
            applies_to=["POST /api/orders"],
        ),
        BusinessRuleSurface(
            name="r3",
            rule_kind="validation",
            expression="POST /api/orders body field 'customer': required",
            applies_to=["POST /api/orders"],
        ),
    ]
    screen = ScreenSurface(
        name="OrderForm",
        screen_name="OrderForm",
        route_ref="/orders/new",
        fields=[ScreenField(name="customer", required=True)],
        actions=[ScreenAction(trigger="submit", api_ref="POST /api/orders")],
    )
    api.enrichment = {
        "given_when_then": [
            {
                "given": "a signed-in clerk",
                "when": "they place an order",
                "then": "an order id is returned",
            }
        ]
    }
    return SurfaceCollection(
        apis=[api, pay],
        models=[model],
        workflows=[wf],
        business_rules=rules,
        screens=[screen],
    )


def _generate(
    tmp_path: Path,
) -> tuple[list[Path], SurfaceCollection, list[WrittenBean]]:
    coll = _collection()
    feats = cluster_surfaces(coll)
    beans = [
        WrittenBean(
            bean_number=i,
            bean_id=f"BEAN-{i:03d}",
            slug="x",
            surface_type=s.surface_type,
            title=s.name,
            path=tmp_path / f"BEAN-{i:03d}-x.md",
        )
        for i, s in enumerate(coll, start=1)
    ]
    write_features_and_manifest(tmp_path, "demo", coll, feats, beans)
    return generate_gherkin(coll, tmp_path, beans), coll, beans


def test_all_feature_files_parse_and_are_traceable(tmp_path: Path) -> None:
    files, _coll, _beans = _generate(tmp_path)
    assert files
    parser = Parser()
    for path in files:
        doc = parser.parse(path.read_text())
        feature = doc["feature"]
        assert feature["name"]
        scenarios = [c["scenario"] for c in feature["children"] if "scenario" in c]
        assert scenarios
        for sc in scenarios:
            tags = {t["name"] for t in sc["tags"]}
            assert any(re.fullmatch(r"@BEAN-\d+", t) for t in tags), sc["name"]
            assert "@generated" in tags and any(t.startswith("@FEAT-") for t in tags)


def test_negative_and_lifecycle_scenarios_present(tmp_path: Path) -> None:
    files, _c, _b = _generate(tmp_path)
    text = "\n".join(f.read_text() for f in files)
    assert "rejects a missing customer" in text
    assert (
        "violates the rule \"POST /api/orders body field 'customer': minimum length 3\""
        in text
    )
    assert "access is denied" in text
    assert "Scenario Outline: OrderStatus: pay is rejected from other states" in text
    pay_outline = text.split("OrderStatus: pay is rejected from other states")[1].split(
        "Scenario"
    )[0]
    assert "| PAID |" in pay_outline and "| SHIPPED |" in pay_outline
    assert "| DRAFT |" not in pay_outline
    ship_outline = text.split("OrderStatus: ship is rejected from other states")[
        1
    ].split("Scenario")[0]
    assert "| DRAFT |" in ship_outline and "| PAID |" not in ship_outline
    assert "the response status is 400" in text
    assert "a signed-in clerk" in text  # enrichment triple carried through
    assert "unique" in text
    # The 'required' body-field rule duplicates the API scenario and is skipped.
    assert (
        "input violates the rule \"POST /api/orders body field 'customer': required\""
        not in text
    )


def test_scenarios_are_implementation_neutral(tmp_path: Path) -> None:
    files, _c, _b = _generate(tmp_path)
    for path in files:
        for line in path.read_text().splitlines():
            if line.strip().startswith(("Given", "When", "Then", "And", "Scenario")):
                assert not FORBIDDEN.search(line), line


def test_unknown_contracts_are_tagged_gap_and_paths_normalized(tmp_path: Path) -> None:
    files, _c, _b = _generate(tmp_path)
    text = "\n".join(f.read_text() for f in files)
    head = text.split("Scenario: POST /api/orders/{order_id}/pay succeeds")[0]
    assert "@gap" in head.splitlines()[-2]
    assert "<int:order_id>" not in text


def test_deterministic_and_skips_without_manifest(tmp_path: Path) -> None:
    a, _c, _b = (
        _generate(tmp_path / "a")
        if (tmp_path / "a").mkdir() is None
        else ([], None, None)
    )
    b, _c2, _b2 = (
        _generate(tmp_path / "b")
        if (tmp_path / "b").mkdir() is None
        else ([], None, None)
    )
    assert [p.read_text() for p in a] == [p.read_text() for p in b]
    assert generate_gherkin(SurfaceCollection(), tmp_path / "none", []) == []
    assert json.loads((tmp_path / "a" / "build-manifest.json").read_text())
