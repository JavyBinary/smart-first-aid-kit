"""FastAPI application entrypoint for MedAI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from medai.auth import (
    Argon2PasswordHasher,
    AuthService,
    InMemoryRateLimiter,
    PostgresSessionStore,
    PostgresUserStore,
    TokenCodec,
    create_auth_router,
)
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

__all__ = ["create_app"]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app(
    config: Config | None = None,
    auth_service: AuthService | None = None,
    dialog_service: DialogService | None = None,
    kit_store: KitStore | None = None,
    profile_store: ProfileStore | None = None,
) -> FastAPI:
    app_config = load_config() if config is None else config
    configure_logging(app_config.logging)

    engine = create_engine(app_config.database)

    if auth_service is None:
        user_store = PostgresUserStore(engine)
        session_store = PostgresSessionStore(engine)
        hasher = Argon2PasswordHasher()
        tokens = TokenCodec(app_config.auth)
        limiter = InMemoryRateLimiter(app_config.auth.rate_limit)

        service = AuthService(
            config=app_config.auth,
            users=user_store,
            sessions=session_store,
            hasher=hasher,
            tokens=tokens,
            limiter=limiter,
        )
    else:
        service = auth_service

    if dialog_service is None:
        history_store = PostgresHistoryStore(engine)
        event_broker = InMemoryDialogEventBroker()

        pkg_path = find_data_dir() / "medicines" / "package.yaml"

        analyzer = MorphAnalyzer()
        bm25_index = (
            load_package_from_yaml(pkg_path, analyzer) if pkg_path.exists() else None
        )

        d_service = DialogService(
            history_store=history_store,
            event_broker=event_broker,
            bm25_index=bm25_index,
            analyzer=analyzer,
        )
    else:
        d_service = dialog_service

    k_store = PostgresKitStore(engine) if kit_store is None else kit_store
    p_store = PostgresProfileStore(engine) if profile_store is None else profile_store

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await d_service.shutdown()
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

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check() -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "medai-backend",
            "version": "0.1.0",
        }

    return app


app = create_app()
