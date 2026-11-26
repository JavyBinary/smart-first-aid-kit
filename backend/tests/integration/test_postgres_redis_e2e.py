"""Live Postgres + Redis integration tests (run when MEDAI_INTEGRATION=1)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from medai.admin.models import ReportStatus, StatsPeriod
from medai.admin.stores import PostgresAdminStore
from medai.auth.models import Role, TooManyAttemptsError
from medai.auth.postgres import PostgresUserStore
from medai.cache.blacklist import RedisTokenBlacklist
from medai.cache.rate_limiter import RedisRateLimiter
from medai.config import AuthRateLimitConfig, DatabaseConfig
from medai.db.engine import create_engine
from medai.db.tables import metadata
from medai.dialogs.postgres import PostgresHistoryStore
from medai.kit.models import CreateKitItemRequest
from medai.kit.postgres import PostgresKitStore
from medai.profile.models import UpdateHealthProfileRequest
from medai.profile.postgres import PostgresProfileStore
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import find_data_dir
from medai.rag.models import MedicineDocument
from medai.rag.postgres import PostgresRagStore

INTEGRATION_ENABLED = os.getenv("MEDAI_INTEGRATION", "").strip() == "1"

pytestmark = pytest.mark.skipif(
    not INTEGRATION_ENABLED,
    reason="Set MEDAI_INTEGRATION=1 with live PostgreSQL + Redis to run integration tests",
)


@pytest.mark.asyncio
async def test_live_postgres_and_redis_end_to_end() -> None:
    dsn = os.getenv(
        "MEDAI_TEST_DATABASE_URL",
        "postgresql+asyncpg://medai:medai@127.0.0.1:55432/medai_test",
    )
    redis_url = os.getenv("MEDAI_TEST_REDIS_URL", "redis://127.0.0.1:56379/0")

    engine = create_engine(DatabaseConfig(url=dsn))
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    user_store = PostgresUserStore(engine)
    kit_store = PostgresKitStore(engine)
    profile_store = PostgresProfileStore(engine)
    dialog_store = PostgresHistoryStore(engine)
    admin_store = PostgresAdminStore(engine)
    rag_store = PostgresRagStore(engine, MorphAnalyzer())

    # 1. Users, Kit with tags, Health Profile
    user = await user_store.create(
        id=uuid4(),
        email=f"int_{uuid4().hex[:6]}@medai.ru",
        name="Интеграция",
        password_hash="hash_1",
        role=Role.ADMIN,
        avatar_color="#00A86B",
        now=datetime.now(UTC),
    )
    item = await kit_store.add_item(
        user.id,
        CreateKitItemRequest(
            name="Ибупрофен",
            dosage="400 мг",
            form="таблетки",
            category="Обезболивающие",
            tags=["жар", "боль"],
            quantity=2,
            expiry="2028-01-01",
            status="otc",
        ),
    )
    assert item.tags == ["жар", "боль"]
    loaded_kit = await kit_store.list_items(user.id)
    assert len(loaded_kit) == 1 and loaded_kit[0].tags == ["жар", "боль"]

    prof = await profile_store.update_profile(
        user.id,
        UpdateHealthProfileRequest(
            age=31,
            weight_kg=74.0,
            chronic_diseases=["Гастрит"],
            allergies=["Пенициллин"],
            special_notes="После еды",
        ),
    )
    assert prof.chronic_diseases == ["Гастрит"]

    # 2. Dialogs, Feedback, Reports & Admin stats
    dialog_id = await dialog_store.create_dialog(user.id)
    m1, m2 = await dialog_store.append_exchange(
        user.id,
        dialog_id,
        "Болит голова",
        "Рекомендую парацетамол.",
        rag_payload={"used_llm": False},
        title="Головная боль",
    )
    await dialog_store.set_feedback(user.id, dialog_id, m2.id, 5)
    report_id = await dialog_store.create_report(
        user.id, dialog_id, m2.id, "inaccurate", "Тестовая жалоба"
    )
    assert report_id > 0
    await admin_store.set_report_status(report_id, ReportStatus.RESOLVED, user.id)
    stats = await admin_store.get_stats(StatsPeriod.DAYS_30, fallback_medicines_count=20)
    assert stats.users_total == 1
    assert stats.feedback.counts[4] == 1
    assert stats.dialogs == 1 and stats.messages == 2 and m1.role == "user"

    # 3. RAG Postgres load, search, trigram, export, delete, restore
    pkg_path = find_data_dir() / "medicines" / "package.yaml"
    load_res = await rag_store.replace_from_yaml(pkg_path)
    assert load_res.document_count >= 20
    assert load_res.chunk_count >= 20
    hybrid = await rag_store.load_into_hybrid_index()
    assert hybrid is not None
    hits = hybrid.search_hybrid("высокая температура и боль", top_k=3)
    assert hits and hits[0].doc_id
    fuzzy = await rag_store.suggest_fuzzy("Ибупрафен")
    assert any("ибупрофен" in d.title.lower() for d in fuzzy)

    extra_doc = MedicineDocument(
        id="D99",
        title="ТестМед",
        inn="Тестамин",
        atc_code="N02BE99",
        category="Анальгетики",
        forms=["таблетки"],
        indications=["тест"],
        contraindications=[],
        dosage="1 таблетка в сутки.",
        interactions=[],
        emergency_flags=[],
    )
    await rag_store.upsert_medicine(extra_doc)
    assert len(await rag_store.list_medicines()) == load_res.document_count + 1
    exported_pkg = await rag_store.export_package()
    assert len(exported_pkg.medicines) == load_res.document_count + 1
    assert await rag_store.delete_medicine("D99") is True
    restored = await rag_store.restore_revision("D99")
    assert restored is not None and restored.id == "D99"

    # 4. Redis RateLimiter & Token Blacklist
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(redis_url, decode_responses=False)
    await redis_client.flushdb()
    rl = RedisRateLimiter(
        redis_client,
        AuthRateLimitConfig(
            login_per_ip=2,
            login_per_ip_window_seconds=60,
            login_failures=2,
            login_failure_window_seconds=60,
        ),
    )
    await rl.check_login_ip("10.0.0.1")
    await rl.check_login_ip("10.0.0.1")
    with pytest.raises(TooManyAttemptsError):
        await rl.check_login_ip("10.0.0.1")

    bl = RedisTokenBlacklist(redis_client)
    jti = "test-jti-123"
    assert await bl.is_revoked(jti) is False
    await bl.revoke(jti, ttl_seconds=60)
    assert await bl.is_revoked(jti) is True

    await redis_client.aclose()
    await engine.dispose()
