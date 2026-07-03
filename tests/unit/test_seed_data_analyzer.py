"""Tests for the seed/reference data analyzer (BEAN-066)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.seed_data import (
    MAX_VALUES_PER_DATASET,
    analyze_seed_data,
)
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.inventory import scan


def _inventory(tmp_path: Path):
    config = HarvestConfig(repo=str(tmp_path), llm_enabled=False)
    return scan(tmp_path, config)


def _write(tmp_path: Path, rel: str, content: str) -> None:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestPythonEnums:
    def test_strenum_members_extracted(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "status.py",
            "from enum import StrEnum\n\n"
            "class OrderStatus(StrEnum):\n"
            '    DRAFT = "draft"\n'
            '    PAID = "paid"\n',
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        enums = [s for s in surfaces if s.kind == "enum"]
        assert len(enums) == 1
        assert enums[0].dataset_name == "OrderStatus"
        assert {"name": "DRAFT", "value": "draft"} in enums[0].values
        assert enums[0].surface_type == "seed_data"

    def test_non_enum_class_ignored(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "models.py",
            "class User:\n    NAME = 'x'\n",
        )
        assert analyze_seed_data(tmp_path, _inventory(tmp_path)) == []


class TestTypescriptEnums:
    def test_ts_enum_with_values(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/color.ts",
            'export enum Color {\n  Red = "red",\n  Blue = "blue",\n}\n',
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        assert len(surfaces) == 1
        assert surfaces[0].dataset_name == "Color"
        assert {"name": "Red", "value": "red"} in surfaces[0].values

    def test_ts_numeric_enum(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/level.ts",
            "enum Level {\n  Low = 1,\n  High = 10,\n}\n",
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        assert {"name": "High", "value": 10} in surfaces[0].values


class TestSqlInserts:
    def test_multi_row_insert_becomes_lookup_table(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "migrations/seed.sql",
            "INSERT INTO roles (id, name) VALUES (1, 'admin'), (2, 'member');\n",
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        assert len(surfaces) == 1
        surface = surfaces[0]
        assert surface.kind == "lookup_table"
        assert surface.target_model_ref == "roles"
        assert {"id": 1, "name": "admin"} in surface.values
        assert {"id": 2, "name": "member"} in surface.values

    def test_null_and_string_literals(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "seed.sql",
            "INSERT INTO tags (id, label) VALUES (1, NULL), (2, 'a,b');\n",
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        values = surfaces[0].values
        assert {"id": 1, "label": None} in values
        assert {"id": 2, "label": "a,b"} in values


class TestFixturesAndTruncation:
    def test_json_fixture_rows(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "fixtures/countries.json",
            '[{"code": "US"}, {"code": "CA"}]',
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        assert len(surfaces) == 1
        assert surfaces[0].kind == "fixture"
        assert surfaces[0].dataset_name == "countries"
        assert len(surfaces[0].values) == 2

    def test_truncation_is_flagged_not_silent(self, tmp_path: Path) -> None:
        rows = ", ".join(f"({i}, 'v{i}')" for i in range(MAX_VALUES_PER_DATASET + 10))
        _write(
            tmp_path,
            "seed.sql",
            f"INSERT INTO big (id, v) VALUES {rows};\n",  # noqa: S608 - fixture text, not a query
        )
        surfaces = analyze_seed_data(tmp_path, _inventory(tmp_path))
        assert surfaces[0].truncated is True
        assert len(surfaces[0].values) == MAX_VALUES_PER_DATASET

    def test_invalid_json_fixture_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path, "fixtures/broken.json", "{not json")
        assert analyze_seed_data(tmp_path, _inventory(tmp_path)) == []
