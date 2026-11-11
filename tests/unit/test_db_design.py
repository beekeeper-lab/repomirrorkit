"""Tests for the DB design bundle (BEAN-072)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import jsonschema

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelRelationship,
    ModelSurface,
    SeedDataSurface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.generator.db_design import generate_db_design


def _models() -> list[ModelSurface]:
    user = ModelSurface(
        name="User",
        entity_name="User",
        persistence_refs=["users"],
        fields=[
            ModelField("id", "db.Integer", ["primary_key"]),
            ModelField("email", "db.String(255)", ["unique", "not_null"]),
            ModelField("age", "int", ["ge=18"]),
            ModelField("blob", "Weird<Type>", []),
        ],
    )
    post = ModelSurface(
        name="Post",
        entity_name="Post",
        persistence_refs=["posts"],
        fields=[
            ModelField("id", "Integer", ["primary_key"]),
            ModelField("user_id", "Integer", ["not_null"]),
            ModelField("title", "String", ["max_length=100", "min_length=3"]),
        ],
        relationship_details=[
            ModelRelationship(
                source_model="Post",
                target_model="User",
                kind="many_to_one",
                fk_column="user_id",
            )
        ],
    )
    return [post, user]  # deliberately child-first: DDL must reorder


def _run(tmp_path: Path, **extra: object) -> Path:
    coll = SurfaceCollection(models=_models(), **extra)  # type: ignore[arg-type]
    files = generate_db_design(coll, tmp_path, "demo")
    assert files
    return tmp_path / "db-design"


def test_ddl_loads_in_sqlite_with_fk_order_and_constraints(tmp_path: Path) -> None:
    root = _run(tmp_path)
    ddl = (root / "schema.sql").read_text()
    assert ddl.index('CREATE TABLE "users"') < ddl.index('CREATE TABLE "posts"')
    assert 'FOREIGN KEY ("user_id") REFERENCES "users" ("id")' in ddl
    assert 'CHECK ("age" >= 18)' in ddl and 'CHECK (length("title") >= 3)' in ddl
    assert "GAP: original type 'Weird<Type>'" in ddl

    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ddl)
    con.execute("INSERT INTO users (id, email, age) VALUES (1, 'a@b.c', 20)")
    con.execute("INSERT INTO posts (id, user_id, title) VALUES (1, 1, 'hello')")
    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO posts (id, user_id, title) VALUES (2, 99, 'orphan')")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO users (id, email, age) VALUES (2, 'x@y.z', 5)")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO users (id, email, age) VALUES (3, 'a@b.c', 30)")


def test_json_schema_per_entity_valid_and_matches_fields(tmp_path: Path) -> None:
    root = _run(tmp_path)
    for model in _models():
        schema = json.loads(
            (root / "entities" / f"{model.name}.schema.json").read_text()
        )
        jsonschema.Draft202012Validator.check_schema(schema)
        assert set(schema["properties"]) == {f.name for f in model.fields}
    user = json.loads((root / "entities" / "User.schema.json").read_text())
    assert user["properties"]["email"]["maxLength"] == 255
    assert user["properties"]["age"]["minimum"] == 18
    assert "email" in user["required"]
    jsonschema.validate({"id": 1, "email": "a@b.c", "age": 20, "blob": "x"}, user)


def test_seed_sql_and_enum_schema_enrichment(tmp_path: Path) -> None:
    seeds = [
        SeedDataSurface(
            name="roles",
            dataset_name="roles",
            kind="lookup_table",
            target_model_ref="User",
            values=[{"id": 1, "email": "root@example.com", "age": 40, "ignored": "x"}],
        ),
        SeedDataSurface(
            name="UserAge",
            dataset_name="UserAge",
            kind="enum",
            values=[{"name": "A", "value": 1}],
        ),
    ]
    root = _run(tmp_path, seed_data=seeds)
    sql = (root / "seed-data.sql").read_text()
    assert (
        'INSERT INTO "users" ("id", "email", "age") VALUES (1, \'root@example.com\', 40);'
        in sql
    )
    con = sqlite3.connect(":memory:")
    con.executescript((root / "schema.sql").read_text())
    con.executescript(sql)
    assert con.execute("select count(*) from users").fetchone() == (1,)
    user = json.loads((root / "entities" / "User.schema.json").read_text())
    assert user["properties"]["age"]["enum"] == [1]
    assert len(json.loads((root / "seed-data.json").read_text())["datasets"]) == 2


def test_readme_lists_gaps_and_no_models_skips(tmp_path: Path) -> None:
    root = _run(tmp_path)
    readme = (root / "README.md").read_text()
    assert (
        "unmapped type 'Weird<Type>'" in readme
        and "No seed/reference datasets" in readme
    )
    assert generate_db_design(SurfaceCollection(), tmp_path / "x", "demo") == []


def test_quotes_in_values_are_escaped(tmp_path: Path) -> None:
    seeds = [
        SeedDataSurface(
            name="s",
            dataset_name="s",
            kind="fixture",
            target_model_ref="User",
            values=[{"id": 1, "email": "o'brien@x.y"}],
        )
    ]
    root = _run(tmp_path, seed_data=seeds)
    con = sqlite3.connect(":memory:")
    con.executescript((root / "schema.sql").read_text())
    con.executescript((root / "seed-data.sql").read_text())
    assert con.execute("select email from users").fetchone() == ("o'brien@x.y",)
