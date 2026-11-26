"""Add RAG chunked index, revisions, pg_trgm, user kit tags, feedback, reports, and audio.

Revision ID: 0002_rag_hybrid_feedback_admin
Revises: 0001_initial_schema
Create Date: 2026-11-26 04:22:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_rag_hybrid_feedback_admin"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add tags column to user_kits
    op.add_column(
        "user_kits",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )

    # rag_chunks
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("doc_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "section", sa.Text(), server_default=sa.text("'general'"), nullable=False
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("term_count", sa.Integer(), nullable=False),
        sa.Column(
            "embedding",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doc_id"], ["rag_medicines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doc_id", "position", name="rag_chunks_doc_position_key"),
    )
    op.create_index("rag_chunks_doc_id_idx", "rag_chunks", ["doc_id"], unique=False)

    # rag_terms
    op.create_table(
        "rag_terms",
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("df", sa.Integer(), nullable=False),
        sa.CheckConstraint("df >= 1", name="rag_terms_df_positive"),
        sa.PrimaryKeyConstraint("term"),
    )

    # rag_postings
    op.create_table(
        "rag_postings",
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("chunk_id", sa.BigInteger(), nullable=False),
        sa.Column("tf", sa.Integer(), nullable=False),
        sa.CheckConstraint("tf >= 1", name="rag_postings_tf_positive"),
        sa.ForeignKeyConstraint(["chunk_id"], ["rag_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("term", "chunk_id"),
    )
    op.create_index(
        "rag_postings_chunk_id_idx", "rag_postings", ["chunk_id"], unique=False
    )

    # rag_stats
    op.create_table(
        "rag_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("n_chunks", sa.Integer(), nullable=False),
        sa.Column("avgdl", sa.Float(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("id = 1", name="rag_stats_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )

    # rag_loads
    op.create_table(
        "rag_loads",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "operation", sa.Text(), server_default=sa.text("'load'"), nullable=False
        ),
        sa.Column(
            "document_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "term_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "operation IN ('load', 'delete', 'restore')",
            name="rag_loads_operation_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # rag_revisions
    op.create_table(
        "rag_revisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("doc_id", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'delete', 'restore')",
            name="rag_revisions_operation_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doc_id", "revision", name="rag_revisions_doc_rev_key"),
    )
    op.create_index(
        op.f("ix_rag_revisions_doc_id"), "rag_revisions", ["doc_id"], unique=False
    )

    # message_feedback
    op.create_table(
        "message_feedback",
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
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
            "score >= 1 AND score <= 5", name="message_feedback_score_valid"
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id"),
    )

    # message_reports
    op.create_table(
        "message_reports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("dialog_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "dialog_title", sa.Text(), server_default=sa.text("''"), nullable=False
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), server_default=sa.text("'new'"), nullable=False
        ),
        sa.Column(
            "dialog_deleted", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('new', 'resolved', 'dismissed')",
            name="message_reports_status_valid",
        ),
        sa.ForeignKeyConstraint(["dialog_id"], ["dialogs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(
        op.f("ix_message_reports_user_id"), "message_reports", ["user_id"], unique=False
    )

    # message_audio
    op.create_table(
        "message_audio",
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("voice_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.Text(), nullable=False),
        sa.Column(
            "mime_type",
            sa.Text(),
            server_default=sa.text("'audio/mpeg'"),
            nullable=False,
        ),
        sa.Column("audio_data", sa.LargeBinary(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
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
            "status IN ('pending', 'ready', 'failed')",
            name="message_audio_status_valid",
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "voice_id"),
    )

    # PostgreSQL trigram fuzzy matching support for medicine names / INN
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS rag_medicines_title_trgm_idx "
        "ON rag_medicines USING gin (lower(title) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS rag_medicines_inn_trgm_idx "
        "ON rag_medicines USING gin (lower(inn) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS rag_medicines_inn_trgm_idx")
    op.execute("DROP INDEX IF EXISTS rag_medicines_title_trgm_idx")
    op.drop_table("message_audio")
    op.drop_index(op.f("ix_message_reports_user_id"), table_name="message_reports")
    op.drop_table("message_reports")
    op.drop_table("message_feedback")
    op.drop_index(op.f("ix_rag_revisions_doc_id"), table_name="rag_revisions")
    op.drop_table("rag_revisions")
    op.drop_table("rag_loads")
    op.drop_table("rag_stats")
    op.drop_index("rag_postings_chunk_id_idx", table_name="rag_postings")
    op.drop_table("rag_postings")
    op.drop_table("rag_terms")
    op.drop_index("rag_chunks_doc_id_idx", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_column("user_kits", "tags")
