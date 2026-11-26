"""FastAPI application entrypoint for MedAI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis.asyncio import Redis

from medai.admin import AdminStore, PostgresAdminStore, create_admin_router
from medai.agent.providers.litellm import LiteLLMProvider
from medai.auth import (
    Argon2PasswordHasher,
    AuthService,
    PostgresSessionStore,
    PostgresUserStore,
    TokenCodec,
    create_auth_router,
)
from medai.cache import RedisRateLimiter, RedisTokenBlacklist
from medai.config import Config, load_config
from medai.db.engine import create_engine
from medai.dialogs import (
    DialogService,
    InMemoryDialogEventBroker,
    PostgresHistoryStore,
    create_dialogs_router,
)
from medai.kit import KitStore, PostgresKitStore, create_kit_router
from medai.observability import RequestLogMiddleware, configure_logging
from medai.profile import PostgresProfileStore, ProfileStore, create_profile_router
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import find_data_dir, load_package_from_yaml
from medai.rag.postgres import PostgresRagStore
from medai.security import ForbiddenOriginMiddleware
from medai.speech import create_speech_router

__all__ = ["create_app"]

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    llm_configured: bool = False


def create_app(
    config: Config | None = None,
    auth_service: AuthService | None = None,
    dialog_service: DialogService | None = None,
    kit_store: KitStore | None = None,
    profile_store: ProfileStore | None = None,
    admin_store: AdminStore | None = None,
) -> FastAPI:
    app_config = load_config() if config is None else config
    configure_logging(app_config.logging)

    engine = create_engine(app_config.database)
    redis_client = Redis.from_url(app_config.redis.url, decode_responses=True)

    if auth_service is None:
        user_store = PostgresUserStore(engine)
        session_store = PostgresSessionStore(engine)
        hasher = Argon2PasswordHasher()
        tokens = TokenCodec(app_config.auth)
        limiter = RedisRateLimiter(redis_client, app_config.auth.rate_limit)
        blacklist = RedisTokenBlacklist(redis_client)

        service = AuthService(
            config=app_config.auth,
            users=user_store,
            sessions=session_store,
            hasher=hasher,
            tokens=tokens,
            limiter=limiter,
            blacklist=blacklist,
        )
    else:
        service = auth_service

    k_store = PostgresKitStore(engine) if kit_store is None else kit_store
    p_store = PostgresProfileStore(engine) if profile_store is None else profile_store
    llm_provider = LiteLLMProvider(app_config.llm)
    analyzer = MorphAnalyzer()
    rag_store = PostgresRagStore(engine, analyzer=analyzer)
    pkg_path = find_data_dir() / "medicines" / "package.yaml"

    if dialog_service is None:
        history_store = PostgresHistoryStore(engine)
        event_broker = InMemoryDialogEventBroker()
        bm25_index = (
            load_package_from_yaml(pkg_path, analyzer) if pkg_path.exists() else None
        )

        d_service = DialogService(
            history_store=history_store,
            event_broker=event_broker,
            bm25_index=bm25_index,
            analyzer=analyzer,
            llm_provider=llm_provider,
            kit_store=k_store,
            profile_store=p_store,
        )
    else:
        d_service = dialog_service

    a_store = PostgresAdminStore(engine) if admin_store is None else admin_store

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Seed PostgreSQL RAG tables from package.yaml if DB is reachable and empty
        try:
            existing_docs = await rag_store.list_medicines()
            if not existing_docs and pkg_path.exists():
                await rag_store.replace_from_yaml(pkg_path)
                existing_docs = await rag_store.list_medicines()
            if existing_docs:
                hybrid = await rag_store.load_into_hybrid_index()
                if hybrid is not None:
                    d_service.set_rag_index(hybrid.bm25)
        except Exception:
            logger.info("PostgreSQL RAG seed skipped; using in-memory YAML index.")

        try:
            yield
        finally:
            await d_service.shutdown()
            await redis_client.aclose()
            await engine.dispose()

    app = FastAPI(
        title="MedAI Backend",
        description="Smart First Aid Kit API (BMSTU NIRS)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.auth_service = service
    app.state.dialog_service = d_service
    app.state.kit_store = k_store
    app.state.profile_store = p_store
    app.state.admin_store = a_store
    app.state.rag_store = rag_store

    app.add_middleware(ForbiddenOriginMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_auth_router(service, app_config.auth))
    app.include_router(create_dialogs_router(d_service))
    app.include_router(create_kit_router(k_store))
    app.include_router(create_profile_router(p_store))
    app.include_router(create_admin_router(a_store, rag_store=rag_store, dialog_service=d_service))
    app.include_router(create_speech_router(d_service))

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check() -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "medai-backend",
            "version": "0.1.0",
            "llm_configured": llm_provider.is_configured,
        }

    return app


app = create_app()
