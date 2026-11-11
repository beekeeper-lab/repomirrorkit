"""Tests for feature clustering and the build manifest (BEAN-069)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    BusinessRuleSurface,
    ConfigSurface,
    ModelField,
    ModelRelationship,
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
    MANIFEST_SCHEMA,
    build_manifest,
    cluster_surfaces,
    resource_key,
    write_features_and_manifest,
)


def _collection() -> SurfaceCollection:
    user = ModelSurface(
        name="User", entity_name="User", fields=[ModelField("name", "str")]
    )
    order = ModelSurface(
        name="Order",
        entity_name="Order",
        fields=[ModelField("user_id", "int")],
        relationship_details=[
            ModelRelationship(
                source_model="Order", target_model="User", kind="many_to_one"
            )
        ],
    )
    apis = [
        ApiSurface(name="GET /api/users", method="GET", path="/api/users"),
        ApiSurface(name="POST /api/orders", method="POST", path="/api/orders"),
        ApiSurface(
            name="POST /api/orders/:id/pay", method="POST", path="/api/orders/:id/pay"
        ),
    ]
    screen = ScreenSurface(
        name="OrderForm",
        screen_name="OrderForm",
        fields=[ScreenField(name="user", bound_model_field="User.name")],
        actions=[ScreenAction(trigger="submit", api_ref="POST /api/orders")],
    )
    wf = ScreenSurface(name="Dashboard", screen_name="Dashboard")
    workflow = WorkflowSurface(
        name="OrderStatus lifecycle",
        entity_ref="OrderStatus",
        transitions=[
            WorkflowTransition(
                "DRAFT", "PAID", trigger="pay", trigger_ref="POST /api/orders/:id/pay"
            )
        ],
    )
    rule = BusinessRuleSurface(
        name="r",
        rule_kind="validation",
        expression="Order.user_id: required",
        applies_to=["Order"],
    )
    cfg = ConfigSurface(name="DATABASE_URL")
    return SurfaceCollection(
        models=[user, order],
        apis=apis,
        screens=[screen, wf],
        workflows=[workflow],
        business_rules=[rule],
        config=[cfg],
    )


def _beans(coll: SurfaceCollection, tmp_path: Path) -> list[WrittenBean]:
    return [
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


def test_resource_key_normalization() -> None:
    assert resource_key("UserForm") == "user"
    assert resource_key("users") == "user"
    assert resource_key("OrderStatus") == "order"
    assert resource_key("Categories") == "category"
    assert resource_key("status") == "status"


def test_every_surface_in_exactly_one_feature() -> None:
    coll = _collection()
    feats = cluster_surfaces(coll)
    assert all(s.feature_id for s in coll)
    member_ids = [id(m) for f in feats for m in f.members]
    assert len(member_ids) == len(set(member_ids)) == len(list(coll))
    names = {f.name: f for f in feats}
    assert "Order management" in names and "User management" in names
    order = names["Order management"]
    kinds = {m.surface_type for m in order.members}
    assert {"api", "model", "screen", "workflow", "business_rule"} <= kinds
    assert feats[0].kind == "platform"  # config → Platform first


def test_feature_dependencies_follow_references() -> None:
    feats = {f.name: f for f in cluster_surfaces(_collection())}
    platform = feats["Platform & Configuration"].id
    order, user = feats["Order management"], feats["User management"]
    assert user.id in order.depends_on  # relationship + bound model field
    assert platform in order.depends_on and platform in user.depends_on


def test_manifest_schema_dag_and_order(tmp_path: Path) -> None:
    coll = _collection()
    feats = cluster_surfaces(coll)
    beans = _beans(coll, tmp_path)
    manifest = build_manifest("demo", coll, feats, beans)
    jsonschema.validate(manifest, MANIFEST_SCHEMA)

    order = manifest["build_order"]["beans"]
    assert sorted(order) == sorted(b["id"] for b in manifest["beans"])
    pos = {b: i for i, b in enumerate(order)}
    for b in manifest["beans"]:
        assert all(pos[d] < pos[b["id"]] for d in b["depends_on"])
    forder = manifest["build_order"]["features"]
    fpos = {f: i for i, f in enumerate(forder)}
    for f in manifest["features"]:
        assert all(fpos[d] < fpos[f["id"]] for d in f["depends_on"])
    by_title = {b["title"]: b for b in manifest["beans"]}
    ids = {b["title"]: b["id"] for b in manifest["beans"]}
    assert ids["User"] in by_title["Order"]["depends_on"]
    assert ids["POST /api/orders"] in by_title["OrderForm"]["depends_on"]


def test_deterministic_manifest_bytes(tmp_path: Path) -> None:
    outputs = []
    for run in ("a", "b"):
        coll = _collection()
        feats = cluster_surfaces(coll)
        out = tmp_path / run
        out.mkdir()
        path = write_features_and_manifest(out, "demo", coll, feats, _beans(coll, out))
        outputs.append(path.read_text())
    assert outputs[0] == outputs[1]


def test_feature_files_link_beans(tmp_path: Path) -> None:
    coll = _collection()
    feats = cluster_surfaces(coll)
    write_features_and_manifest(tmp_path, "demo", coll, feats, _beans(coll, tmp_path))
    text = next((tmp_path / "features").glob("FEAT-*-order-management.md")).read_text()
    assert "](../beans/BEAN-" in text and "## Feature-level acceptance criteria" in text
    assert "POST /api/orders" in text
    manifest = json.loads((tmp_path / "build-manifest.json").read_text())
    assert all(Path(tmp_path / f["path"]).is_file() for f in manifest["features"])
