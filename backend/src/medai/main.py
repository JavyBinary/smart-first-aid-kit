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
from medai.observability import RequestLogMiddleware, configure_logging

__all__ = ["create_app"]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app(
    config: Config | None = None,
    auth_service: AuthService | None = None,
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

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="MedAI Backend",
        description="Smart First Aid Kit API (BMSTU NIRS)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.auth_service = service

    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_auth_router(service, app_config.auth))

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check() -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "medai-backend",
            "version": "0.1.0",
        }

    return app


app = create_app()
