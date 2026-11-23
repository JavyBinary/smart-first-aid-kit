"""FastAPI application entrypoint for MedAI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from medai.config import Config, load_config
from medai.observability import RequestLogMiddleware, configure_logging

__all__ = ["create_app"]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app(config: Config | None = None) -> FastAPI:
    app_config = load_config() if config is None else config
    configure_logging(app_config.logging)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(
        title="MedAI Backend",
        description="Smart First Aid Kit API (BMSTU NIRS)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check() -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "medai-backend",
            "version": "0.1.0",
        }

    return app


app = create_app()
