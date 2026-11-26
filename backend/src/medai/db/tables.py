"""SQLAlchemy Core description of the relational database schema for MedAI.

The schema is documented in specs/changes/018-db-schema-and-migrations/spec.md;
migrations are the source of truth for the database itself.
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# Use JSONB on PostgreSQL, standard JSON elsewhere (e.g. SQLite tests)
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("email", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("role", Text, nullable=False, server_default=text("'user'")),
    Column("avatar_color", Text, nullable=False, server_default=text("'#2563EB'")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("role IN ('user', 'admin', 'superadmin')", name="users_role_valid"),
    CheckConstraint("email ~ '^[^@]+@[^@]+\\.[^@]+$'", name="users_email_format"),
)
Index("users_email_lower_key", func.lower(users.c.email), unique=True)

refresh_sessions = Table(
    "refresh_sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("family_id", Uuid, nullable=False, index=True),
    Column("token_hash", LargeBinary, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
    Column(
        "replaced_by",
        Uuid,
        ForeignKey("refresh_sessions.id", ondelete="SET NULL"),
        nullable=True,
    ),
)

user_kits = Table(
    "user_kits",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("medicine_name", Text, nullable=False),
    Column("dosage", Text, nullable=False),
    Column("form", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("tags", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("status", Text, nullable=False, server_default=text("'otc'")),
    Column("expiry_date", Date, nullable=False),
    Column("quantity", Integer, nullable=False, server_default=text("1")),
    Column("notes", Text, nullable=True),
    Column("icon_color", Text, nullable=False, server_default=text("'#E8F7F0'")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("status IN ('otc', 'rx')", name="user_kits_status_valid"),
    CheckConstraint("quantity >= 1", name="user_kits_quantity_positive"),
)

health_profiles = Table(
    "health_profiles",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    ),
    Column("age", Integer, nullable=False, server_default=text("25")),
    Column("weight_kg", Float, nullable=False, server_default=text("70.0")),
    Column("chronic_diseases", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("allergies", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("special_notes", Text, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("age >= 0 AND age <= 130", name="health_profiles_age_valid"),
    CheckConstraint(
        "weight_kg >= 1.0 AND weight_kg <= 300.0",
        name="health_profiles_weight_valid",
    ),
)

dialogs = Table(
    "dialogs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("title", Text, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)
Index(
    "dialogs_user_id_updated_at_idx",
    dialogs.c.user_id,
    dialogs.c.updated_at.desc(),
)

messages = Table(
    "messages",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column(
        "dialog_id",
        Uuid,
        ForeignKey("dialogs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False),
    Column("role", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("rag_payload", JSON_TYPE, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint("dialog_id", "position", name="messages_dialog_id_position_key"),
    CheckConstraint(
        "role IN ('user', 'assistant', 'system')", name="messages_role_valid"
    ),
)

rag_medicines = Table(
    "rag_medicines",
    metadata,
    Column("id", Text, primary_key=True),
    Column("title", Text, nullable=False),
    Column("inn", Text, nullable=False),
    Column("atc_code", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("forms", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("indications", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("contraindications", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("dosage_text", Text, nullable=False),
    Column("interactions", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column("emergency_flags", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

rag_bm25_index = Table(
    "rag_bm25_index",
    metadata,
    Column(
        "doc_id",
        Text,
        ForeignKey("rag_medicines.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("lemmatized_text", Text, nullable=False),
    Column("doc_length", Integer, nullable=False),
    Column("term_frequencies", JSON_TYPE, nullable=False),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

rag_chunks = Table(
    "rag_chunks",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column(
        "doc_id",
        Text,
        ForeignKey("rag_medicines.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False),
    Column("section", Text, nullable=False, server_default=text("'general'")),
    Column("text", Text, nullable=False),
    Column("term_count", Integer, nullable=False),
    Column("embedding", JSON_TYPE, nullable=False, server_default=text("'[]'")),
    UniqueConstraint("doc_id", "position", name="rag_chunks_doc_position_key"),
)
Index("rag_chunks_doc_id_idx", rag_chunks.c.doc_id)

rag_terms = Table(
    "rag_terms",
    metadata,
    Column("term", Text, primary_key=True),
    Column("df", Integer, nullable=False),
    CheckConstraint("df >= 1", name="rag_terms_df_positive"),
)

rag_postings = Table(
    "rag_postings",
    metadata,
    Column("term", Text, primary_key=True),
    Column(
        "chunk_id",
        BigInteger,
        ForeignKey("rag_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("tf", Integer, nullable=False),
    CheckConstraint("tf >= 1", name="rag_postings_tf_positive"),
)
Index("rag_postings_chunk_id_idx", rag_postings.c.chunk_id)

rag_stats = Table(
    "rag_stats",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("n_chunks", Integer, nullable=False),
    Column("avgdl", Float, nullable=False),
    Column("version", BigInteger, nullable=False),
    CheckConstraint("id = 1", name="rag_stats_singleton"),
)

rag_loads = Table(
    "rag_loads",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("operation", Text, nullable=False, server_default=text("'load'")),
    Column("document_count", Integer, nullable=False, server_default=text("0")),
    Column("chunk_count", Integer, nullable=False, server_default=text("0")),
    Column("term_count", Integer, nullable=False, server_default=text("0")),
    Column(
        "started_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "operation IN ('load', 'delete', 'restore')", name="rag_loads_operation_valid"
    ),
)

rag_revisions = Table(
    "rag_revisions",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("doc_id", Text, nullable=False, index=True),
    Column("revision", Integer, nullable=False),
    Column("operation", Text, nullable=False),
    Column("snapshot", JSON_TYPE, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint("doc_id", "revision", name="rag_revisions_doc_rev_key"),
    CheckConstraint(
        "operation IN ('create', 'update', 'delete', 'restore')",
        name="rag_revisions_operation_valid",
    ),
)

message_feedback = Table(
    "message_feedback",
    metadata,
    Column(
        "message_id",
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("score", Integer, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("score >= 1 AND score <= 5", name="message_feedback_score_valid"),
)

message_reports = Table(
    "message_reports",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column(
        "message_id",
        BigInteger,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    ),
    Column(
        "dialog_id",
        Uuid,
        ForeignKey("dialogs.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("dialog_title", Text, nullable=False, server_default=text("''")),
    Column("reason", Text, nullable=False),
    Column("comment", Text, nullable=True),
    Column("request_text", Text, nullable=False),
    Column("answer_text", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'new'")),
    Column("dialog_deleted", Integer, nullable=False, server_default=text("0")),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column(
        "resolved_by",
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("seen_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "status IN ('new', 'resolved', 'dismissed')",
        name="message_reports_status_valid",
    ),
)

message_audio = Table(
    "message_audio",
    metadata,
    Column(
        "message_id",
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("voice_id", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column("text_hash", Text, nullable=False),
    Column("mime_type", Text, nullable=False, server_default=text("'audio/mpeg'")),
    Column("audio_data", LargeBinary, nullable=True),
    Column("duration_ms", Integer, nullable=True),
    Column("error_code", Text, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint(
        "status IN ('pending', 'ready', 'failed')",
        name="message_audio_status_valid",
    ),
)
