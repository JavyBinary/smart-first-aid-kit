"""Unit tests for MedAI relational database schema, tables, constraints, and engine."""

import importlib

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateTable

from medai.config import DatabaseConfig
from medai.db.engine import create_engine
from medai.db.tables import (
    health_profiles,
    messages,
    metadata,
    rag_bm25_index,
    rag_medicines,
    user_kits,
    users,
)


def test_metadata_contains_all_tables() -> None:
    expected_tables = {
        "users",
        "refresh_sessions",
        "user_kits",
        "health_profiles",
        "dialogs",
        "messages",
        "rag_medicines",
        "rag_bm25_index",
    }
    assert expected_tables.issubset(set(metadata.tables.keys()))


def test_users_table_structure_and_constraints() -> None:
    cols = {c.name: c for c in users.columns}
    assert "id" in cols
    assert "email" in cols
    assert "name" in cols
    assert "password_hash" in cols
    assert "role" in cols
    assert "avatar_color" in cols

    check_names = {c.name for c in users.constraints if isinstance(c, CheckConstraint)}
    assert "users_role_valid" in check_names
    assert "users_email_format" in check_names


def test_user_kits_table_and_constraints() -> None:
    cols = {c.name: c for c in user_kits.columns}
    assert "medicine_name" in cols
    assert "dosage" in cols
    assert "form" in cols
    assert "category" in cols
    assert "status" in cols
    assert "quantity" in cols

    check_names = {
        c.name for c in user_kits.constraints if isinstance(c, CheckConstraint)
    }
    assert "user_kits_status_valid" in check_names
    assert "user_kits_quantity_positive" in check_names

    fks = [c for c in user_kits.constraints if isinstance(c, ForeignKeyConstraint)]
    assert any(fk.referred_table.name == "users" for fk in fks)


def test_health_profiles_table_and_constraints() -> None:
    cols = {c.name: c for c in health_profiles.columns}
    assert "user_id" in cols
    assert "age" in cols
    assert "weight_kg" in cols
    assert "chronic_diseases" in cols
    assert "allergies" in cols

    check_names = {
        c.name for c in health_profiles.constraints if isinstance(c, CheckConstraint)
    }
    assert "health_profiles_age_valid" in check_names
    assert "health_profiles_weight_valid" in check_names

    unique_cols = set()
    for c in health_profiles.constraints:
        if isinstance(c, UniqueConstraint):
            unique_cols.update(col.name for col in c.columns)
    assert "user_id" in unique_cols or health_profiles.c.user_id.unique


def test_dialogs_and_messages_hierarchy() -> None:
    msg_fks = [c for c in messages.constraints if isinstance(c, ForeignKeyConstraint)]
    assert any(fk.referred_table.name == "dialogs" for fk in msg_fks)

    msg_checks = {
        c.name for c in messages.constraints if isinstance(c, CheckConstraint)
    }
    assert "messages_role_valid" in msg_checks

    unique_sets = [
        tuple(col.name for col in c.columns)
        for c in messages.constraints
        if isinstance(c, UniqueConstraint)
    ]
    assert ("dialog_id", "position") in unique_sets


def test_rag_tables_relationship() -> None:
    rag_cols = {c.name for c in rag_medicines.columns}
    assert {
        "id",
        "title",
        "inn",
        "atc_code",
        "category",
        "indications",
        "contraindications",
    }.issubset(rag_cols)

    bm25_fks = [
        c for c in rag_bm25_index.constraints if isinstance(c, ForeignKeyConstraint)
    ]
    assert any(fk.referred_table.name == "rag_medicines" for fk in bm25_fks)


def test_create_engine_configuration() -> None:
    config = DatabaseConfig(url="postgresql+asyncpg://test:test@localhost:5432/testdb")
    engine = create_engine(config)
    assert isinstance(engine, AsyncEngine)
    assert engine.sync_engine.hide_parameters is True


def test_ddl_compilation_postgresql_dialect() -> None:
    """Validate that all table definitions compile cleanly to PostgreSQL DDL."""
    pg_dialect = postgresql.dialect()
    for table_name, table in metadata.tables.items():
        ddl = str(CreateTable(table).compile(dialect=pg_dialect))
        assert f"CREATE TABLE {table_name}" in ddl
        assert len(ddl) > 30


def test_migration_0001_initial_schema_validity() -> None:
    """Validate that baseline migration exists and exports required revision and callbacks."""
    migration_mod = importlib.import_module(
        "medai.db.migrations.versions.0001_initial_schema"
    )
    assert migration_mod.revision == "0001_initial_schema"
    assert migration_mod.down_revision is None
    assert callable(migration_mod.upgrade)
    assert callable(migration_mod.downgrade)
