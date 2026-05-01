"""Tests for the data-model relationships report (BEAN-055)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelRelationship,
    ModelSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.reports.data_model import (
    _mermaid_connector,
    _populate_relationships_from_source,
    _scan_relationships,
    write_data_model_report,
)

# ---------------------------------------------------------------------------
# Source-based extraction
# ---------------------------------------------------------------------------


class TestDjangoExtraction:
    def test_foreign_key_basic(self) -> None:
        src = (
            "class Post(models.Model):\n"
            "    author = models.ForeignKey(User, on_delete=models.CASCADE)\n"
        )
        rels = _scan_relationships(src, "Post", "blog/models.py", {})
        assert len(rels) == 1
        rel = rels[0]
        assert rel.source_model == "Post"
        assert rel.target_model == "User"
        assert rel.kind == "many_to_one"
        assert rel.fk_column == "author"
        assert rel.cascade == "CASCADE"
        assert rel.source_file == "blog/models.py"

    def test_one_to_one(self) -> None:
        src = (
            "class Profile(models.Model):\n"
            "    user = models.OneToOneField(User, on_delete=models.SET_NULL)\n"
        )
        rels = _scan_relationships(src, "Profile", "x.py", {})
        assert rels[0].kind == "one_to_one"
        assert rels[0].cascade == "SET_NULL"

    def test_many_to_many(self) -> None:
        src = (
            "class Post(models.Model):\n"
            "    tags = models.ManyToManyField('Tag')\n"
        )
        rels = _scan_relationships(src, "Post", "x.py", {})
        assert rels[0].kind == "many_to_many"
        assert rels[0].target_model == "Tag"
        assert rels[0].fk_column == "tags"

    def test_strips_app_prefix(self) -> None:
        src = (
            "class Post(models.Model):\n"
            "    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)\n"
        )
        rels = _scan_relationships(src, "Post", "x.py", {})
        assert rels[0].target_model == "User"


class TestSqlAlchemyExtraction:
    def test_foreign_key_column(self) -> None:
        src = (
            "class Post(Base):\n"
            "    user_id = Column(Integer, ForeignKey('users.id'))\n"
        )
        rels = _scan_relationships(src, "Post", "models.py", {})
        # Falls back to the literal table name 'users' since no User model
        # is in by_name for resolution.
        assert any(r.fk_column == "user_id" and r.kind == "many_to_one" for r in rels)

    def test_relationship_call(self) -> None:
        src = (
            "class User(Base):\n"
            "    posts = relationship('Post', back_populates='author')\n"
        )
        rels = _scan_relationships(src, "User", "models.py", {})
        # Relationship call without uselist defaults to one_to_many.
        assert any(r.target_model == "Post" and r.kind == "one_to_many" for r in rels)


# ---------------------------------------------------------------------------
# populate_relationships_from_source: end-to-end
# ---------------------------------------------------------------------------


class TestPopulateRelationships:
    def test_appends_to_relationship_details(self, tmp_path: Path) -> None:
        (tmp_path / "models.py").write_text(
            "class Post(models.Model):\n"
            "    author = models.ForeignKey(User, on_delete=models.CASCADE)\n"
        )
        post = ModelSurface(
            name="Post",
            entity_name="Post",
            source_refs=[SourceRef(file_path="models.py", start_line=1)],
        )
        user = ModelSurface(
            name="User",
            entity_name="User",
        )
        _populate_relationships_from_source([post, user], tmp_path)
        assert len(post.relationship_details) == 1
        assert post.relationship_details[0].target_model == "User"
        # Idempotent: a second pass should not duplicate.
        _populate_relationships_from_source([post, user], tmp_path)
        assert len(post.relationship_details) == 1

    def test_silent_on_missing_file(self, tmp_path: Path) -> None:
        # ModelSurface points at a file that doesn't exist.
        m = ModelSurface(
            name="X",
            entity_name="X",
            source_refs=[SourceRef(file_path="missing.py", start_line=1)],
        )
        _populate_relationships_from_source([m], tmp_path)
        assert m.relationship_details == []


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


class TestRenderReport:
    def test_writes_file_at_top_level(self, tmp_path: Path) -> None:
        path = write_data_model_report(SurfaceCollection(), tmp_path)
        assert path == tmp_path / "data-model.md"
        assert path.is_file()

    def test_empty_surfaces_renders_stub(self, tmp_path: Path) -> None:
        text = write_data_model_report(SurfaceCollection(), tmp_path).read_text()
        assert "# Data Model" in text
        assert "no data-model surfaces detected" in text
        assert "no relationships detected across all models" in text

    def test_models_section_lists_fields(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            models=[
                ModelSurface(
                    name="User",
                    entity_name="User",
                    fields=[
                        ModelField(name="id", field_type="int", constraints=["primary_key"]),
                        ModelField(name="email", field_type="str", constraints=["unique"]),
                    ],
                    source_refs=[SourceRef(file_path="models.py", start_line=10)],
                )
            ]
        )
        text = write_data_model_report(coll, tmp_path).read_text()
        assert "### User" in text
        assert "`id`" in text
        assert "`email`" in text
        assert "primary_key" in text
        assert "models.py" in text

    def test_mermaid_block_emitted_when_relationships_present(
        self, tmp_path: Path
    ) -> None:
        coll = SurfaceCollection(
            models=[
                ModelSurface(
                    name="Post",
                    entity_name="Post",
                    relationship_details=[
                        ModelRelationship(
                            source_model="Post",
                            target_model="User",
                            kind="many_to_one",
                            fk_column="author_id",
                            source_file="models.py",
                        )
                    ],
                ),
                ModelSurface(name="User", entity_name="User"),
            ]
        )
        text = write_data_model_report(coll, tmp_path).read_text()
        assert "```mermaid" in text
        assert "erDiagram" in text
        assert "Post }o--|| User" in text
        assert "author_id" in text

    def test_mermaid_skipped_when_no_relationships(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            models=[ModelSurface(name="User", entity_name="User")]
        )
        text = write_data_model_report(coll, tmp_path).read_text()
        # Mermaid block should NOT be present.
        assert "```mermaid" not in text
        # But the section header should still be there with the stub text.
        assert "## ER Diagram" in text
        assert "no relationships detected" in text

    def test_relationships_table_lists_each_edge(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            models=[
                ModelSurface(
                    name="Post",
                    entity_name="Post",
                    relationship_details=[
                        ModelRelationship(
                            source_model="Post",
                            target_model="User",
                            kind="many_to_one",
                            fk_column="author_id",
                            cascade="CASCADE",
                            source_file="blog/models.py",
                        )
                    ],
                )
            ]
        )
        text = write_data_model_report(coll, tmp_path).read_text()
        assert "## All Relationships" in text
        assert "`Post`" in text
        assert "`User`" in text
        assert "many_to_one" in text
        assert "`author_id`" in text
        assert "CASCADE" in text
        assert "`blog/models.py`" in text

    def test_total_count_in_header(self, tmp_path: Path) -> None:
        coll = SurfaceCollection(
            models=[
                ModelSurface(
                    name="A",
                    entity_name="A",
                    relationship_details=[
                        ModelRelationship(source_model="A", target_model="B", kind="many_to_one"),
                        ModelRelationship(source_model="A", target_model="C", kind="many_to_one"),
                    ],
                ),
                ModelSurface(name="B", entity_name="B"),
                ModelSurface(name="C", entity_name="C"),
            ]
        )
        text = write_data_model_report(coll, tmp_path).read_text()
        assert "**Models:** 3" in text
        assert "**Relationships:** 2" in text


class TestMermaidConnector:
    def test_known_kinds(self) -> None:
        assert _mermaid_connector("one_to_one") == "||--||"
        assert _mermaid_connector("one_to_many") == "||--o{"
        assert _mermaid_connector("many_to_one") == "}o--||"
        assert _mermaid_connector("many_to_many") == "}o--o{"

    def test_unknown_kind_falls_back(self) -> None:
        # Unknown kinds default to one_to_many connector.
        assert _mermaid_connector("nonsense") == "||--o{"
