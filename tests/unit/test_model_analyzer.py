"""Unit tests for the Model & Entity Analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_mirror_kit.harvester.analyzers.models import (
    _extract_alembic,
    _extract_entity_framework,
    _extract_prisma,
    _extract_sql,
    _extract_sqlalchemy,
    _extract_typeorm,
    analyze_models,
)
from repo_mirror_kit.harvester.analyzers.surfaces import ModelField
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(
            path=p,
            size=100,
            extension="." + p.rsplit(".", 1)[-1] if "." in p.rsplit("/", 1)[-1] else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=100 * len(files),
        total_skipped=0,
    )


def _make_profile(stacks: dict[str, float]) -> StackProfile:
    """Build a StackProfile with the given stacks."""
    return StackProfile(
        stacks=stacks,
        evidence={k: [] for k in stacks},
        signals=[],
    )


def _write_file(tmp_path: Path, rel_path: str, content: str) -> None:
    """Write content to a file under tmp_path."""
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Prisma extraction tests
# ---------------------------------------------------------------------------


class TestPrismaExtraction:
    """Tests for Prisma schema model extraction."""

    def test_basic_prisma_model(self, tmp_path: Path) -> None:
        schema = """\
model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  name  String?
  posts Post[]
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        assert len(surfaces) == 1
        user = surfaces[0]
        assert user.entity_name == "User"
        assert user.surface_type == "model"

        field_names = [f.name for f in user.fields]
        assert "id" in field_names
        assert "email" in field_names
        assert "name" in field_names

        # id should have primary_key constraint
        id_field = next(f for f in user.fields if f.name == "id")
        assert "primary_key" in id_field.constraints

        # email should have unique constraint
        email_field = next(f for f in user.fields if f.name == "email")
        assert "unique" in email_field.constraints

        # name is optional (?) so should not have not_null
        name_field = next(f for f in user.fields if f.name == "name")
        assert "not_null" not in name_field.constraints

        # posts should be a relationship, not a field
        assert "posts" not in field_names
        assert any("Post" in r for r in user.relationships)

    def test_prisma_multiple_models(self, tmp_path: Path) -> None:
        schema = """\
model User {
  id    Int    @id
  email String
}

model Post {
  id       Int    @id
  title    String
  authorId Int
  author   User   @relation(fields: [authorId], references: [id])
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        assert len(surfaces) == 2
        names = {s.entity_name for s in surfaces}
        assert names == {"User", "Post"}

    def test_prisma_map_annotation(self, tmp_path: Path) -> None:
        schema = """\
model UserAccount {
  id   Int    @id
  name String

  @@map("user_accounts")
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        assert len(surfaces) == 1
        assert surfaces[0].entity_name == "UserAccount"
        assert "user_accounts" in surfaces[0].persistence_refs

    def test_prisma_source_ref(self, tmp_path: Path) -> None:
        schema = """\
// some comment
model Foo {
  id Int @id
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        assert len(surfaces) == 1
        assert surfaces[0].source_refs[0].file_path == "prisma/schema.prisma"
        assert surfaces[0].source_refs[0].start_line == 2

    def test_prisma_no_schema_files(self, tmp_path: Path) -> None:
        surfaces = _extract_prisma(tmp_path, ["src/app.ts"])
        assert surfaces == []


# ---------------------------------------------------------------------------
# SQLAlchemy extraction tests
# ---------------------------------------------------------------------------


class TestSQLAlchemyExtraction:
    """Tests for SQLAlchemy model extraction."""

    def test_basic_sqlalchemy_model(self, tmp_path: Path) -> None:
        code = """\
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
"""
        _write_file(tmp_path, "src/models.py", code)
        surfaces = _extract_sqlalchemy(tmp_path, ["src/models.py"])
        assert len(surfaces) == 1
        user = surfaces[0]
        assert user.entity_name == "User"
        assert "users" in user.persistence_refs

        field_names = [f.name for f in user.fields]
        assert "id" in field_names
        assert "email" in field_names
        assert "name" in field_names

        id_field = next(f for f in user.fields if f.name == "id")
        assert "primary_key" in id_field.constraints

        email_field = next(f for f in user.fields if f.name == "email")
        assert "unique" in email_field.constraints
        assert "not_null" in email_field.constraints

    def test_sqlalchemy_relationship(self, tmp_path: Path) -> None:
        code = """\
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User")
"""
        _write_file(tmp_path, "src/models.py", code)
        surfaces = _extract_sqlalchemy(tmp_path, ["src/models.py"])
        assert len(surfaces) == 1
        post = surfaces[0]
        assert any("User" in r for r in post.relationships)
        assert any("users.id" in r for r in post.relationships)

    def test_sqlalchemy_flask_db_model(self, tmp_path: Path) -> None:
        code = """\
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
"""
        _write_file(tmp_path, "src/models.py", code)
        surfaces = _extract_sqlalchemy(tmp_path, ["src/models.py"])
        assert len(surfaces) == 1
        assert surfaces[0].entity_name == "Item"

    def test_sqlalchemy_no_tablename(self, tmp_path: Path) -> None:
        code = """\
class Product(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
"""
        _write_file(tmp_path, "src/models.py", code)
        surfaces = _extract_sqlalchemy(tmp_path, ["src/models.py"])
        assert len(surfaces) == 1
        # Fallback to lowercase class name
        assert "product" in surfaces[0].persistence_refs

    def test_sqlalchemy_no_model_files(self, tmp_path: Path) -> None:
        surfaces = _extract_sqlalchemy(tmp_path, ["src/utils.py"])
        assert surfaces == []


# ---------------------------------------------------------------------------
# Entity Framework extraction tests
# ---------------------------------------------------------------------------


class TestEntityFrameworkExtraction:
    """Tests for Entity Framework C# entity extraction."""

    def test_basic_ef_entity(self, tmp_path: Path) -> None:
        dbcontext = """\
using Microsoft.EntityFrameworkCore;

public class AppDbContext : DbContext
{
    public DbSet<User> Users { get; set; }
    public DbSet<Order> Orders { get; set; }
}
"""
        entity = """\
public class User
{
    public int Id { get; set; }
    public string Email { get; set; }
    public string Name { get; set; }
}
"""
        _write_file(tmp_path, "Data/AppDbContext.cs", dbcontext)
        _write_file(tmp_path, "Models/User.cs", entity)
        surfaces = _extract_entity_framework(
            tmp_path,
            ["Data/AppDbContext.cs", "Models/User.cs"],
        )
        user_surfaces = [s for s in surfaces if s.entity_name == "User"]
        assert len(user_surfaces) == 1
        user = user_surfaces[0]
        field_names = [f.name for f in user.fields]
        assert "Id" in field_names
        assert "Email" in field_names

        # Id property should get primary_key constraint
        id_field = next(f for f in user.fields if f.name == "Id")
        assert "primary_key" in id_field.constraints

    def test_ef_with_annotations(self, tmp_path: Path) -> None:
        code = """\
public class AppDbContext : DbContext
{
    public DbSet<Product> Products { get; set; }
}

[Table("products")]
public class Product
{
    [Key]
    public int ProductId { get; set; }

    [Required]
    public string Name { get; set; }

    public decimal Price { get; set; }
}
"""
        _write_file(tmp_path, "Data/Context.cs", code)
        surfaces = _extract_entity_framework(tmp_path, ["Data/Context.cs"])
        product_surfaces = [s for s in surfaces if s.entity_name == "Product"]
        assert len(product_surfaces) == 1
        product = product_surfaces[0]
        assert "products" in product.persistence_refs

        pid = next(f for f in product.fields if f.name == "ProductId")
        assert "primary_key" in pid.constraints

        pname = next(f for f in product.fields if f.name == "Name")
        assert "not_null" in pname.constraints

    def test_ef_navigation_properties(self, tmp_path: Path) -> None:
        code = """\
public class AppDbContext : DbContext
{
    public DbSet<Order> Orders { get; set; }
}

public class Order
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public ICollection<OrderItem> Items { get; set; }
}
"""
        _write_file(tmp_path, "Models/Order.cs", code)
        surfaces = _extract_entity_framework(tmp_path, ["Models/Order.cs"])
        order_surfaces = [s for s in surfaces if s.entity_name == "Order"]
        assert len(order_surfaces) == 1
        order = order_surfaces[0]
        # ICollection should become a relationship
        assert any("Items" in r for r in order.relationships)
        # UserId should be detected as FK
        assert any("UserId" in r for r in order.relationships)

    def test_ef_no_cs_files(self, tmp_path: Path) -> None:
        surfaces = _extract_entity_framework(tmp_path, ["src/app.py"])
        assert surfaces == []


# ---------------------------------------------------------------------------
# TypeORM extraction tests
# ---------------------------------------------------------------------------


class TestTypeORMExtraction:
    """Tests for TypeORM/Sequelize decorator extraction."""

    def test_basic_typeorm_entity(self, tmp_path: Path) -> None:
        code = """\
import { Entity, PrimaryGeneratedColumn, Column } from 'typeorm';

@Entity()
class User {
    @PrimaryGeneratedColumn()
    id: number;

    @Column()
    email: string;

    @Column()
    name: string;
}
"""
        _write_file(tmp_path, "src/entity/user.entity.ts", code)
        surfaces = _extract_typeorm(tmp_path, ["src/entity/user.entity.ts"])
        assert len(surfaces) == 1
        user = surfaces[0]
        assert user.entity_name == "User"

        field_names = [f.name for f in user.fields]
        assert "id" in field_names
        assert "email" in field_names

        id_field = next(f for f in user.fields if f.name == "id")
        assert "primary_key" in id_field.constraints

    def test_typeorm_with_relations(self, tmp_path: Path) -> None:
        code = """\
import { Entity, PrimaryGeneratedColumn, Column, ManyToOne } from 'typeorm';

@Entity()
class Post {
    @PrimaryGeneratedColumn()
    id: number;

    @Column()
    title: string;

    @ManyToOne(() => User)
    author: User;
}
"""
        _write_file(tmp_path, "src/entity/post.entity.ts", code)
        surfaces = _extract_typeorm(tmp_path, ["src/entity/post.entity.ts"])
        assert len(surfaces) == 1
        post = surfaces[0]
        assert any("author" in r for r in post.relationships)

    def test_typeorm_no_entity_decorator(self, tmp_path: Path) -> None:
        code = """\
class UserDto {
    name: string;
    email: string;
}
"""
        _write_file(tmp_path, "src/entity/user.model.ts", code)
        surfaces = _extract_typeorm(tmp_path, ["src/entity/user.model.ts"])
        assert surfaces == []

    def test_typeorm_no_matching_files(self, tmp_path: Path) -> None:
        surfaces = _extract_typeorm(tmp_path, ["src/app.ts"])
        assert surfaces == []


# ---------------------------------------------------------------------------
# Plain SQL extraction tests
# ---------------------------------------------------------------------------


class TestSQLExtraction:
    """Tests for plain SQL CREATE TABLE extraction."""

    def test_basic_create_table(self, tmp_path: Path) -> None:
        sql = """\
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100)
);
"""
        _write_file(tmp_path, "migrations/001_init.sql", sql)
        surfaces = _extract_sql(tmp_path, ["migrations/001_init.sql"])
        assert len(surfaces) == 1
        users = surfaces[0]
        assert users.entity_name == "Users"
        assert "users" in users.persistence_refs

        field_names = [f.name for f in users.fields]
        assert "id" in field_names
        assert "email" in field_names
        assert "name" in field_names

        id_field = next(f for f in users.fields if f.name == "id")
        assert "primary_key" in id_field.constraints

        email_field = next(f for f in users.fields if f.name == "email")
        assert "not_null" in email_field.constraints
        assert "unique" in email_field.constraints

    def test_create_table_with_fk(self, tmp_path: Path) -> None:
        sql = """\
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users,
    total DECIMAL(10, 2)
);
"""
        _write_file(tmp_path, "migrations/002_orders.sql", sql)
        surfaces = _extract_sql(tmp_path, ["migrations/002_orders.sql"])
        assert len(surfaces) == 1
        orders = surfaces[0]
        assert any("users" in r for r in orders.relationships)

    def test_create_table_if_not_exists(self, tmp_path: Path) -> None:
        sql = """\
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200)
);
"""
        _write_file(tmp_path, "migrations/003_products.sql", sql)
        surfaces = _extract_sql(tmp_path, ["migrations/003_products.sql"])
        assert len(surfaces) == 1
        assert surfaces[0].entity_name == "Products"

    def test_multiple_tables_in_one_file(self, tmp_path: Path) -> None:
        sql = """\
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    label VARCHAR(50)
);
"""
        _write_file(tmp_path, "migrations/004_taxonomy.sql", sql)
        surfaces = _extract_sql(tmp_path, ["migrations/004_taxonomy.sql"])
        assert len(surfaces) == 2
        names = {s.entity_name for s in surfaces}
        assert names == {"Categories", "Tags"}

    def test_sql_no_sql_files(self, tmp_path: Path) -> None:
        surfaces = _extract_sql(tmp_path, ["src/app.py"])
        assert surfaces == []

    def test_sql_quoted_table_name(self, tmp_path: Path) -> None:
        sql = """\
CREATE TABLE "user_roles" (
    id INTEGER PRIMARY KEY,
    role_name VARCHAR(50)
);
"""
        _write_file(tmp_path, "migrations/005_roles.sql", sql)
        surfaces = _extract_sql(tmp_path, ["migrations/005_roles.sql"])
        assert len(surfaces) == 1
        assert surfaces[0].entity_name == "UserRoles"
        assert "user_roles" in surfaces[0].persistence_refs


# ---------------------------------------------------------------------------
# Alembic extraction tests
# ---------------------------------------------------------------------------


class TestAlembicExtraction:
    """Tests for Alembic migration extraction."""

    def test_basic_create_table(self, tmp_path: Path) -> None:
        code = """\
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255)),
        sa.Column('name', sa.String(100)),
    )
"""
        _write_file(tmp_path, "alembic/versions/001_init.py", code)
        surfaces = _extract_alembic(tmp_path, ["alembic/versions/001_init.py"])
        assert len(surfaces) == 1
        users = surfaces[0]
        assert users.entity_name == "Users"
        assert "users" in users.persistence_refs

        field_names = [f.name for f in users.fields]
        assert "id" in field_names
        assert "email" in field_names
        assert "name" in field_names

    def test_add_column(self, tmp_path: Path) -> None:
        code = """\
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('age', sa.Integer()))
"""
        _write_file(tmp_path, "alembic/versions/002_add_age.py", code)
        surfaces = _extract_alembic(tmp_path, ["alembic/versions/002_add_age.py"])
        assert len(surfaces) == 1
        users = surfaces[0]
        assert users.entity_name == "Users"
        age_field = next((f for f in users.fields if f.name == "age"), None)
        assert age_field is not None
        assert age_field.field_type == "Integer()"

    def test_alembic_source_ref(self, tmp_path: Path) -> None:
        code = """\
# revision
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('items',
        sa.Column('id', sa.Integer()),
    )
"""
        _write_file(tmp_path, "alembic/versions/003_items.py", code)
        surfaces = _extract_alembic(tmp_path, ["alembic/versions/003_items.py"])
        assert len(surfaces) == 1
        assert surfaces[0].source_refs[0].file_path == "alembic/versions/003_items.py"

    def test_alembic_no_migration_files(self, tmp_path: Path) -> None:
        surfaces = _extract_alembic(tmp_path, ["src/models.py"])
        assert surfaces == []


# ---------------------------------------------------------------------------
# Orchestrator (analyze_models) tests
# ---------------------------------------------------------------------------


class TestAnalyzeModels:
    """Tests for the top-level analyze_models orchestrator."""

    def test_prisma_detected(self, tmp_path: Path) -> None:
        schema = """\
model User {
  id    Int    @id
  email String
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        inventory = _make_inventory(["prisma/schema.prisma"])
        profile = _make_profile({"prisma": 0.9})

        surfaces = analyze_models(tmp_path, inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].entity_name == "User"

    def test_sqlalchemy_detected(self, tmp_path: Path) -> None:
        code = """\
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
"""
        _write_file(tmp_path, "src/models.py", code)
        inventory = _make_inventory(["src/models.py"])
        profile = _make_profile({"sqlalchemy": 0.7})

        surfaces = analyze_models(tmp_path, inventory, profile)
        assert len(surfaces) == 1
        assert surfaces[0].entity_name == "User"

    def test_no_data_stacks_returns_empty(self, tmp_path: Path) -> None:
        inventory = _make_inventory(["src/app.py"])
        profile = _make_profile({"react": 0.9})

        surfaces = analyze_models(tmp_path, inventory, profile)
        assert surfaces == []

    def test_deduplication(self, tmp_path: Path) -> None:
        """Same entity from multiple sources should be deduplicated."""
        sa_code = """\
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
"""
        sql = """\
CREATE TABLE users (
    id INTEGER PRIMARY KEY
);
"""
        _write_file(tmp_path, "src/models.py", sa_code)
        _write_file(tmp_path, "migrations/001.sql", sql)
        inventory = _make_inventory(["src/models.py", "migrations/001.sql"])
        profile = _make_profile({"sqlalchemy": 0.7, "sql-migrations": 0.5})

        surfaces = analyze_models(tmp_path, inventory, profile)
        # User appears from both SQLAlchemy and SQL — should be deduplicated
        user_surfaces = [
            s
            for s in surfaces
            if s.entity_name.lower() == "user" or s.entity_name.lower() == "users"
        ]
        assert len(user_surfaces) == 1

    def test_multiple_technologies(self, tmp_path: Path) -> None:
        """Multiple data technologies should all be processed."""
        sa_code = """\
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
"""
        alembic_code = """\
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('orders',
        sa.Column('id', sa.Integer()),
    )
"""
        _write_file(tmp_path, "src/models.py", sa_code)
        _write_file(tmp_path, "alembic/versions/001_init.py", alembic_code)
        inventory = _make_inventory(["src/models.py", "alembic/versions/001_init.py"])
        profile = _make_profile({"sqlalchemy": 0.7, "alembic": 0.9})

        surfaces = analyze_models(tmp_path, inventory, profile)
        names = {s.entity_name for s in surfaces}
        assert "User" in names
        assert "Orders" in names


# ---------------------------------------------------------------------------
# ModelSurface data integrity tests
# ---------------------------------------------------------------------------


class TestModelSurfaceIntegrity:
    """Verify ModelSurface objects have correct structure."""

    def test_surface_type_is_model(self, tmp_path: Path) -> None:
        schema = """\
model Foo {
  id Int @id
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        assert surfaces[0].surface_type == "model"

    def test_to_dict_serialization(self, tmp_path: Path) -> None:
        schema = """\
model Bar {
  id   Int    @id
  name String
}
"""
        _write_file(tmp_path, "prisma/schema.prisma", schema)
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        d = surfaces[0].to_dict()
        assert d["entity_name"] == "Bar"
        assert d["surface_type"] == "model"
        assert isinstance(d["fields"], list)
        assert isinstance(d["relationships"], list)
        assert isinstance(d["persistence_refs"], list)
        assert isinstance(d["source_refs"], list)

    def test_model_field_frozen(self) -> None:
        """ModelField should be immutable (frozen dataclass)."""
        f = ModelField(name="id", field_type="Integer", constraints=["primary_key"])
        with pytest.raises(AttributeError):
            f.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for model extraction."""

    def test_empty_inventory(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        profile = _make_profile({"prisma": 0.9})
        surfaces = analyze_models(tmp_path, inventory, profile)
        assert surfaces == []

    def test_unreadable_file(self, tmp_path: Path) -> None:
        """Files that don't exist should be skipped gracefully."""
        surfaces = _extract_prisma(tmp_path, ["nonexistent/schema.prisma"])
        assert surfaces == []

    def test_empty_prisma_schema(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "prisma/schema.prisma", "")
        surfaces = _extract_prisma(tmp_path, ["prisma/schema.prisma"])
        assert surfaces == []

    def test_empty_sql_file(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "migrations/001.sql", "")
        surfaces = _extract_sql(tmp_path, ["migrations/001.sql"])
        assert surfaces == []

    def test_sql_with_no_columns(self, tmp_path: Path) -> None:
        sql = "CREATE TABLE empty_table ();"
        _write_file(tmp_path, "migrations/001.sql", sql)
        surfaces = _extract_sql(tmp_path, ["migrations/001.sql"])
        # Should create a surface even with no columns
        assert len(surfaces) == 1
        assert surfaces[0].fields == []
