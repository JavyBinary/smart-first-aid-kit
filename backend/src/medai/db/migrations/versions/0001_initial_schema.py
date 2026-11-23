"""Initial database schema for MedAI.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), server_default=sa.text("'user'"), nullable=False),
        sa.Column(
            "avatar_color",
            sa.Text(),
            server_default=sa.text("'#2563EB'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'admin', 'superadmin')", name="users_role_valid"
        ),
        sa.CheckConstraint(
            "email ~ '^[^@]+@[^@]+\\.[^@]+$'", name="users_email_format"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "users_email_lower_key", "users", [sa.text("lower(email)")], unique=True
    )

    # 2. refresh_sessions
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["replaced_by"], ["refresh_sessions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_refresh_sessions_family_id"),
        "refresh_sessions",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_sessions_user_id"),
        "refresh_sessions",
        ["user_id"],
        unique=False,
    )

    # 3. user_kits
    op.create_table(
        "user_kits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("medicine_name", sa.Text(), nullable=False),
        sa.Column("dosage", sa.Text(), nullable=False),
        sa.Column("form", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'otc'"), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "icon_color",
            sa.Text(),
            server_default=sa.text("'#E8F7F0'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('otc', 'rx')", name="user_kits_status_valid"),
        sa.CheckConstraint("quantity >= 1", name="user_kits_quantity_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_kits_user_id"), "user_kits", ["user_id"], unique=False
    )

    # 4. health_profiles
    op.create_table(
        "health_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("age", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column(
            "weight_kg", sa.Float(), server_default=sa.text("70.0"), nullable=False
        ),
        sa.Column(
            "chronic_diseases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "allergies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("special_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("age >= 0 AND age <= 130", name="health_profiles_age_valid"),
        sa.CheckConstraint(
            "weight_kg >= 1.0 AND weight_kg <= 300.0",
            name="health_profiles_weight_valid",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # 5. dialogs
    op.create_table(
        "dialogs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "dialogs_user_id_updated_at_idx",
        "dialogs",
        ["user_id", sa.text("updated_at DESC")],
        unique=False,
    )

    # 6. messages
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("dialog_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "rag_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')", name="messages_role_valid"
        ),
        sa.ForeignKeyConstraint(["dialog_id"], ["dialogs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dialog_id", "position", name="messages_dialog_id_position_key"
        ),
    )

    # 7. rag_medicines
    op.create_table(
        "rag_medicines",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("inn", sa.Text(), nullable=False),
        sa.Column("atc_code", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column(
            "forms",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "indications",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "contraindications",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("dosage_text", sa.Text(), nullable=False),
        sa.Column(
            "interactions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "emergency_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. rag_bm25_index
    op.create_table(
        "rag_bm25_index",
        sa.Column("doc_id", sa.Text(), nullable=False),
        sa.Column("lemmatized_text", sa.Text(), nullable=False),
        sa.Column("doc_length", sa.Integer(), nullable=False),
        sa.Column(
            "term_frequencies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doc_id"], ["rag_medicines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("doc_id"),
    )


def downgrade() -> None:
    op.drop_table("rag_bm25_index")
    op.drop_table("rag_medicines")
    op.drop_table("messages")
    op.drop_index("dialogs_user_id_updated_at_idx", table_name="dialogs")
    op.drop_table("dialogs")
    op.drop_table("health_profiles")
    op.drop_index(op.f("ix_user_kits_user_id"), table_name="user_kits")
    op.drop_table("user_kits")
    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_family_id"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_index("users_email_lower_key", table_name="users")
    op.drop_table("users")
