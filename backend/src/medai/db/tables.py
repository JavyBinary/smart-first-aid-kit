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
